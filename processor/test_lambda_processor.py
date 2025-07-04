import os
import zipfile
import pytest
import lambda_processor
import json

from botocore.exceptions import ClientError

def test_formatar_tamanho_zero():
    assert lambda_processor.formatar_tamanho(0) == "0B"

def test_formatar_tamanho_bytes_and_kb_mb():
    assert lambda_processor.formatar_tamanho(1023) == "1023.0 B"
    assert lambda_processor.formatar_tamanho(1024) == "1.0 KB"
    assert lambda_processor.formatar_tamanho(1024**2) == "1.0 MB"

def test_generate_timestamp_monkeypatched(monkeypatch):
    class FixedDatetime:
        @classmethod
        def now(cls):
            from datetime import datetime as _D
            return _D(2021, 1, 1, 12, 0, 0)
    monkeypatch.setattr(lambda_processor, 'datetime', FixedDatetime)
    assert lambda_processor.generate_timestamp() == "01/01/2021 12:00:00"

def test_generate_s3_presigned_url_success(monkeypatch):
    class FakeS3:
        def generate_presigned_url(self, *args, **kwargs):
            return "http://test"
    fake_s3 = FakeS3()
    monkeypatch.setattr(lambda_processor, 's3_client', fake_s3)
    url = lambda_processor.generate_s3_presigned_url("bucket", "key")
    assert url == "http://test"

def test_generate_s3_presigned_url_error(monkeypatch):
    class FakeS3:
        def generate_presigned_url(self, *args, **kwargs):
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "Op")
    fake_s3 = FakeS3()
    monkeypatch.setattr(lambda_processor, 's3_client', fake_s3)
    assert lambda_processor.generate_s3_presigned_url("bucket", "key") is None

def test_download_file_from_s3_success(tmp_path, monkeypatch):
    fake_bucket = 'bucket'
    fake_key = 'path/to/file.txt'
    fake_content = b'hello'

    class FakeS3:
        pass

    fake_s3 = FakeS3()
    def fake_download_file(bucket, key, filename):
        assert bucket == fake_bucket
        assert key == fake_key
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(fake_content)

    fake_s3.download_file = fake_download_file
    monkeypatch.setattr(lambda_processor, 's3_client', fake_s3)

    result = lambda_processor.download_file_from_s3(fake_bucket, fake_key, str(tmp_path))
    expected = os.path.join(str(tmp_path), os.path.basename(fake_key))
    assert result == expected
    with open(result, 'rb') as f:
        assert f.read() == fake_content

def test_download_file_from_s3_error(monkeypatch):
    class FakeS3:
        pass
    fake_s3 = FakeS3()
    def fake_download_file(bucket, key, filename):
        raise Exception("fail")
    fake_s3.download_file = fake_download_file
    monkeypatch.setattr(lambda_processor, 's3_client', fake_s3)
    assert lambda_processor.download_file_from_s3('b', 'k', '/tmp') is None

def test_extract_frames_and_count(monkeypatch, tmp_path):
    video_path = str(tmp_path / "video.mp4")
    open(video_path, 'a').close()
    prefix, timestamp = "pre", "123"

    class FakeProc:
        pass

    fake_proc = FakeProc()
    def fake_run(cmd, *args, **kwargs):
        out_dir = cmd[-1].rsplit('/frame', 1)[0]
        os.makedirs(out_dir, exist_ok=True)
        for i in range(1, 4):
            open(os.path.join(out_dir, f"frame_{i:04d}.jpg"), 'w').close()

    fake_proc.run = fake_run
    monkeypatch.setattr(lambda_processor, 'subprocess', fake_proc)

    out_dir, num = lambda_processor.extract_frames_and_count(video_path, prefix, timestamp)
    assert os.path.isdir(out_dir)
    assert num == 3

def test_create_zip_archive_success(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    filenames = ["a.txt", "b.txt"]
    for fname in filenames:
        with open(frames_dir / fname, 'w') as f:
            f.write("data")
    zip_path, size = lambda_processor.create_zip_archive(str(frames_dir), "p", "t")
    assert os.path.exists(zip_path)
    assert size > 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        assert set(zf.namelist()) == set(filenames)

def test_create_zip_archive_error():
    assert lambda_processor.create_zip_archive("/nonexistent", "p", "t") == (None, 0)

def test_upload_file_to_s3_success(monkeypatch):
    class FakeS3:
        pass
    fake_s3 = FakeS3()
    def fake_upload_file(file_path, bucket, key):
        return None
    fake_s3.upload_file = fake_upload_file
    monkeypatch.setattr(lambda_processor, 's3_client', fake_s3)
    assert lambda_processor.upload_file_to_s3("file", "bucket", "key") is True

def test_upload_file_to_s3_error(monkeypatch):
    class FakeS3:
        pass
    fake_s3 = FakeS3()
    def fake_upload_file(file_path, bucket, key):
        raise Exception("fail")
    fake_s3.upload_file = fake_upload_file
    monkeypatch.setattr(lambda_processor, 's3_client', fake_s3)
    assert lambda_processor.upload_file_to_s3("file", "bucket", "key") is False

def test_save_metadata_success(monkeypatch):
    class FakeTable:
        name = "table"
        def put_item(self, Item):
            pass

    class FakeDB:
        def Table(self, name):
            return FakeTable()

    monkeypatch.setattr(lambda_processor, 'dynamodb', FakeDB())
    monkeypatch.setattr(lambda_processor, 'DDB_TABLE', 'table')
    assert lambda_processor.save_metadata("uuid", "in", "out") is True

def test_save_metadata_error(monkeypatch):
    class FakeTable:
        def put_item(self, Item):
            raise Exception("fail")

    class FakeDB:
        def Table(self, name):
            return FakeTable()

    monkeypatch.setattr(lambda_processor, 'dynamodb', FakeDB())
    monkeypatch.setattr(lambda_processor, 'DDB_TABLE', 'table')
    assert lambda_processor.save_metadata("uuid", "in", "out") is False

def test_publish_sns_notification_success(monkeypatch, caplog):
    class FakeSQS:
        def send_message(self, QueueUrl=None, MessageBody=None):
            assert QueueUrl == "https://queue.test/url"
            assert isinstance(MessageBody, str)
            json.loads(MessageBody)
            return {"MessageId": "abc123"}

    monkeypatch.setattr(lambda_processor, "sqs_client", FakeSQS(), raising=True)
    monkeypatch.setattr(lambda_processor, "SQS_QUEUE_URL", "https://queue.test/url", raising=True)

    result = lambda_processor.publish_sqs_notification({"foo": "bar"})

    assert result == "abc123"
    assert "Mensagem enviada com sucesso para SQS. MessageId: abc123" in caplog.text


def test_publish_sns_notification_error(monkeypatch, caplog):
    class FakeSNS:
        def publish(self, TopicArn=None, Message=None, Subject=None):
            raise ClientError({"Error": {"Code": "InternalError", "Message": "Oops"}}, "Publish")

    monkeypatch.setenv("SQS_QUEUE_URL", "arn:aws:sns:us-east-1:123456789012:MeuTopico")
    monkeypatch.setattr(lambda_processor, "sqs_client", FakeSNS(), raising=True)

    msg_id = lambda_processor.publish_sqs_notification({"foo": "bar"})

    assert msg_id is None
    assert "Um erro inesperado ocorreu ao publicar no SNS" in caplog.text


def test_process_message_invalid_filename(monkeypatch):
    record = {
        "body": json.dumps({
            "Records": [
                {"s3": {"bucket": {"name": "bkt"}, "object": {"key": "badfilenamemp4"}}}
            ]
        })
    }

    calls = {}

    # Mock para o get_user_email_from_s3_metadata
    class FakeS3:
        def head_object(self, **kw):
            calls['head'] = kw
            return {
                'Metadata': {
                    'user-email': 'usuario@exemplo.com'
                }
            }
    monkeypatch.setattr(lambda_processor, 's3_client', FakeS3(), raising=False)

    # Configurar variáveis de ambiente necessárias
    monkeypatch.setattr(lambda_processor, 'SENDER_EMAIL', 'sender@exemplo.com')

    # Mock para a função publish_sqs_notification
    def fake_publish(msg):
        calls['publish'] = (msg)
        return "msg-id-123"
    monkeypatch.setattr(lambda_processor, 'publish_sqs_notification', fake_publish)

    # Mock para generate_timestamp
    def fake_timestamp():
        return "01/07/2025 14:30:00"
    monkeypatch.setattr(lambda_processor, 'generate_timestamp', fake_timestamp)

    result = lambda_processor.process_message(record)

    # Verificações
    assert result is None
    assert 'head' in calls
    assert 'publish' in calls
    assert 'usuario@exemplo.com' in str(calls['publish']['receiver_email'])
    assert 'badfilenamemp4' in str(calls['publish']['placeholders']['FILE_NAME'])
    assert 'O nome do arquivo enviado é inválido. Por favor, ajuste o nome para que siga o padrão.' in str(
        calls['publish']['placeholders']['ERROR_MESSAGE']
    )

def test_process_message_success(monkeypatch):
    key = "meuvideo_161803398.mp4"
    record = {
        "body": json.dumps({
            "Records": [
                {"s3": {"bucket": {"name": "src-bucket"}, "object": {"key": key}}}
            ]
        })
    }
    calls = {}

    class FakeS3:
        def head_object(self, **kw):
            calls['head'] = kw
            # Adiciona resposta mockada com metadados incluindo email do usuário
            return {
                'ContentLength': 1024,
                'ContentType': 'video/mp4',
                'Metadata': {
                    'user-email': 'usuario@exemplo.com',
                    'user-id': 'user-123456'
                }
            }
    monkeypatch.setattr(lambda_processor, 's3_client', FakeS3(), raising=False)

    # Configure variáveis de ambiente necessárias
    monkeypatch.setattr(lambda_processor, 'SENDER_EMAIL', 'sender@exemplo.com')
    monkeypatch.setattr(lambda_processor, 'OUTPUT_BUCKET', 'output-bucket')
    monkeypatch.setattr(lambda_processor, 'SQS_QUEUE_URL', 'https://sqs.region.amazonaws.com/123456789/queue')

    def fake_download(bucket, k, dest):
        calls['download'] = (bucket, k, dest)
        return "/tmp/test_video.mp4"
    monkeypatch.setattr(lambda_processor, 'download_file_from_s3', fake_download)

    def fake_extract(path, prefix, ts):
        calls['extract'] = (path, prefix, ts)
        return ("/tmp/frames", 4)
    monkeypatch.setattr(lambda_processor, 'extract_frames_and_count', fake_extract)

    def fake_zip(frames_dir, prefix, ts):
        calls['zip'] = (frames_dir, prefix, ts)
        return ("/tmp/archive.zip", 2048)
    monkeypatch.setattr(lambda_processor, 'create_zip_archive', fake_zip)

    def fake_presign(bucket, k):
        calls.setdefault('presign', []).append((bucket, k))
        return "https://download.link"
    monkeypatch.setattr(lambda_processor, 'generate_s3_presigned_url', fake_presign)

    def fake_upload(path, bucket, k):
        calls['upload'] = (path, bucket, k)
        return True
    monkeypatch.setattr(lambda_processor, 'upload_file_to_s3', fake_upload)

    def fake_save(pref, inp, url):
        calls['save'] = (pref, inp, url)
        return True
    monkeypatch.setattr(lambda_processor, 'save_metadata', fake_save)

    def fake_publish(msg):
        calls['publish'] = (msg)
        return "msg-xyz"
    monkeypatch.setattr(lambda_processor, 'publish_sqs_notification', fake_publish)

    lambda_processor.process_message(record)

    assert calls['head'] == {'Bucket': 'src-bucket', 'Key': key}
    assert calls['download'][0:2] == ("src-bucket", key)
    assert calls['extract'] == ("/tmp/test_video.mp4", "meuvideo", "161803398")
    assert calls['zip'] == ("/tmp/frames", "meuvideo", "161803398")

    expect_key = "meuvideo/161803398.zip"
    assert calls['presign'][0] == (lambda_processor.OUTPUT_BUCKET, expect_key)
    assert calls['presign'][1] == (lambda_processor.OUTPUT_BUCKET, expect_key)

    assert calls['upload'] == ("/tmp/archive.zip", lambda_processor.OUTPUT_BUCKET, expect_key)
    assert calls['save'] == ("meuvideo", f"s3://src-bucket/{key}", "https://download.link")

