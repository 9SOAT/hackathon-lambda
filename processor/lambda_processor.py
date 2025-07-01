import json
import logging
import os
import subprocess
import zipfile

import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

# Environment variables (set via Terraform or console)
INPUT_BUCKET = os.getenv("INPUT_BUCKET")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")
DDB_TABLE = os.getenv("DDB_TABLE")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")
FFMPEG_BIN = "/opt/bin/ffmpeg"


def lambda_handler(event, context):
    """Ingress entrypoint. Triggered by SQS with S3 payload."""
    for record in event.get("Records", []):
        try:
            process_message(record)
        except Exception as err:
            logger.error(f"[lambda_handler] Error: {err}", exc_info=True)
            # Optional: re-raise for retry or send to DLQ


def process_message(record):
    """
    Parse SQS message and execute workflow:
    - HeadObject (permission/metadata validation)
    - download, frame extraction, zip, upload, persistence, notification
    """
   

    body = json.loads(record["body"])
    logger.info(f"[process_message] Payload: {body}")

    s3_event = body["Records"][0]["s3"]
    bucket_name = s3_event["bucket"]["name"]
    object_key = s3_event["object"]["key"]

    filename = os.path.basename(object_key)
    try:
        prefix, timestamp, _ext = filename.rsplit('.', 2)
    except ValueError:
        logger.error(f"Nome de arquivo inesperado, não foi possível extrair prefix/timestamp: {filename}")
        # Se não conseguimos nem parsear, não há como continuar
        return

    logger.info(f"Iniciando job para {filename} → pasta '{prefix}', arquivo '{timestamp}.zip'")


    # Validate metadata before download
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
    except ClientError as err:
        error_code = err.response["Error"]["Code"]
        logger.error(f"HeadObject failed: {error_code}")
        raise

    destination = f"/tmp/{prefix}_{timestamp}.mp4"
    local_video_path = download_file_from_s3(bucket_name, object_key, destination)
    frames_dir, num_frames = extract_frames_and_count(local_video_path, prefix, timestamp)
    zip_path, zip_size_bytes  = create_zip_archive(frames_dir, prefix, timestamp)

    zip_key = f"{prefix}/{timestamp}.zip"
    output_s3_uri = f"s3://{OUTPUT_BUCKET}/{zip_key}"
    download_url = generate_s3_presigned_url(OUTPUT_BUCKET, zip_key)
    
    upload_file_to_s3(zip_path, OUTPUT_BUCKET, zip_key)
    save_metadata(prefix, f"s3://{bucket_name}/{object_key}", download_url)

    download_url = generate_s3_presigned_url(OUTPUT_BUCKET, zip_key)
    if download_url:
        logger.info(f"Link para download (válido por 1 hora): {download_url}")
    else:
        logger.warning("Não foi possível gerar o link de download.")

    message = {"receiver_email":"matheus.francesquini@gmail.com","sender_email":"matheus.francesquini@gmail.com","template_name":"SUCCESS_EMAIL_TEMPLATE",
               "placeholders":{"FIRST_NAME":"Matheus","FILE_NAME":download_url,"PROCESS_DATE":generate_timestamp(),"FILE_SIZE":formatar_tamanho(zip_size_bytes),"RECORDS_COUNT": num_frames}}

    publish_sns_notification("Processamento concluído", message)


def download_file_from_s3(bucket: str, key: str, local_dir: str = "/tmp") -> str:
    """
    Baixa um arquivo do S3 para um diretório local.

    Args:
        bucket (str): O nome do bucket S3.
        key (str): A chave (caminho completo) do objeto no bucket.
        local_dir (str): O diretório local para salvar o arquivo (padrão: "/tmp").

    Returns:
        O caminho completo para o arquivo baixado em caso de sucesso, ou None em caso de erro.
    """
    filename = os.path.basename(key)
    destination = os.path.join(local_dir, filename)
    
    os.makedirs(local_dir, exist_ok=True)

    logger.info(f"Baixando s3://{bucket}/{key} para {destination}")

    try:
        s3_client.download_file(bucket, key, destination)
        logger.info("Download concluído com sucesso.")
        return destination

    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante o download: {e}")
        return None


def extract_frames_and_count(video_path: str, prefix: str, timestamp: str) -> tuple[str, int]:
    """
    Extrai frames de um vídeo, conta o total de imagens geradas e as salva em um diretório.

    Retorna uma tupla contendo:
    - O caminho do diretório de saída (str).
    - O número de frames extraídos (int).
    """
    out_dir = f"/tmp/frames_{prefix}_{timestamp}"
    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        FFMPEG_BIN,
        "-i",
        video_path,
        "-vf",
        "fps=1",  # Extrai 1 frame por segundo
        f"{out_dir}/frame_%04d.jpg",
    ]

    logger.info(f"Executando FFmpeg: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True) # Usar capture_output=True é bom para suprimir a saída no terminal

    try:
        num_frames = len(os.listdir(out_dir))
        logger.info(f"Sucesso! {num_frames} frames foram extraídos para {out_dir}")
    except FileNotFoundError:
        logger.error(f"O diretório de saída {out_dir} não foi encontrado após a execução do FFmpeg.")
        num_frames = 0

    return out_dir, num_frames


def create_zip_archive(frames_dir: str, prefix: str, timestamp: str) -> tuple[str, int]:
    """
    Cria um arquivo ZIP compactado a partir de um diretório de imagens.

    Args:
        frames_dir (str): O caminho para o diretório contendo os frames.
        prefix (str): O prefixo para o nome do arquivo ZIP.
        timestamp (str): O timestamp para o nome do arquivo ZIP.

    Returns:
        Uma tupla contendo o caminho do arquivo ZIP e seu tamanho em bytes.
        Retorna (None, 0) em caso de erro.
    """
    zip_path = f"/tmp/{prefix}_{timestamp}.zip"
    
    try:
        logger.info(f"Iniciando a criação do arquivo ZIP: {zip_path}")

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            image_files = os.listdir(frames_dir)

            for fname in image_files:
                full_path = os.path.join(frames_dir, fname)
                zf.write(full_path, arcname=fname)

        zip_size_bytes = os.path.getsize(zip_path)
        logger.info(f"Arquivo ZIP criado com sucesso! Tamanho: {zip_size_bytes} bytes.")
        return zip_path, zip_size_bytes
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado ao criar o ZIP: {e}")
        return None, 0


def upload_file_to_s3(file_path: str, bucket: str, key: str) -> bool:
    """
    Realiza o upload de um arquivo local para o S3.

    Args:
        file_path (str): O caminho para o arquivo local que será enviado.
        bucket (str): O nome do bucket S3 de destino.
        key (str): A chave (caminho) onde o objeto será salvo no bucket.

    Returns:
        True se o upload for bem-sucedido, False em caso de erro.
    """
    logger.info(f"Iniciando upload de {file_path} para s3://{bucket}/{key}")

    try:
        s3_client.upload_file(file_path, bucket, key)
        logger.info("Upload concluído com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante o upload: {e}")
        return False

    
def save_metadata(user_uuid: str,input_key: str, output_key: str,status: str = "COMPLETED") -> bool:
    """
    Salva um item de metadados em uma tabela do DynamoDB.

    Args:
        user_uuid (str): A chave de partição (Partition Key).
        input_key (str): A chave do objeto de entrada no S3.
        output_key (str): A chave do objeto de saída no S3.
        status (str): O status do processo (padrão: "COMPLETED").

    Returns:
        True se a operação for bem-sucedida, False em caso de erro.
    """
    try:

        table = dynamodb.Table(DDB_TABLE)
        item = {
            "user_uuid": user_uuid,
            "timestamp": generate_timestamp(),
            "input_key": input_key,
            "output_key": output_key,
            "status": status,
        }

        logger.info(f"Gravando metadados na tabela '{table.name}': {item}")
        table.put_item(Item=item)
        logger.info("Metadados gravados com sucesso.")
        return True

    except Exception as e:
        logger.error(f"Um erro inesperado ocorreu: {e}")
        return False


def publish_sns_notification(subject: str, message_body):
    
    try:
        topic_arn = "arn:aws:sns:us-east-1:897722698720:disparo-de-emails-topic"
        logger.info(f"Publicando mensagem no tópico SNS: {topic_arn}")
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=json.dumps(message_body)
        )
        message_id = response.get("MessageId")
        logger.info(f"Mensagem publicada com sucesso. MessageId: {message_id}")
        return message_id
    except Exception as e:
        logger.error(f"Um erro inesperado ocorreu ao publicar no SNS: {e}")
        return None

def generate_timestamp() -> str:
    """
    Gera um timestamp em string no formato DDMMYYYYHHMMSS.
    """
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    
def formatar_tamanho(size_bytes: int) -> str:
    """Converte um tamanho em bytes para um formato legível (KB, MB, GB)."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def generate_s3_presigned_url(bucket_name: str, object_key: str, expiration: int = 3600):
    """
    Gera uma URL pré-assinada para download de um objeto do S3.

    Args:
        bucket_name (str): O nome do bucket.
        object_key (str): A chave do objeto no bucket.
        expiration (int): Tempo de validade da URL em segundos (padrão: 3600 = 1 hora).

    Returns:
        A URL pré-assinada como string, ou None em caso de erro.
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Não foi possível gerar a URL pré-assinada: {e}")
        return None