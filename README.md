# Hackathon Lambda

## Descrição do Projeto

Este projeto consiste em funções AWS Lambda desenvolvidas para fornecer serviços essenciais em uma arquitetura serverless. O sistema inclui duas funções principais que trabalham com serviços da AWS para entrega de e-mails e gerenciamento de uploads de arquivos.

### Funcionalidades

#### 1. Sistema de Notificação via E-mail (notification)
Uma função Lambda que processa mensagens de uma fila SQS e envia e-mails personalizados utilizando o Amazon SES (Simple Email Service). A função:

- Utiliza templates pré-configurados no SES para envio de e-mails
- Suporta personalização de mensagens através de placeholders
- Processa mensagens de uma fila para comunicação assíncrona
- Fornece tratamento de erros e logs para rastreabilidade

#### 2. Gerador de URLs Pré-assinadas (presigned)
Uma função Lambda que gera URLs pré-assinadas do S3 para upload seguro de arquivos. A função:

- Gera URLs temporárias para upload direto ao S3, sem necessidade de credenciais AWS
- Utiliza autenticação JWT para validar solicitações
- Nomeia os arquivos com base no ID do usuário e timestamp
- Define políticas de expiração para os links gerados

## Tecnologias Utilizadas

- **AWS Lambda** - Computação serverless para execução das funções
- **Amazon SES** - Serviço de envio de e-mails
- **Amazon S3** - Armazenamento de objetos
- **Amazon SQS** - Filas de mensagens para processamento assíncrono
- **Python** - Linguagem de programação utilizada
- **Boto3** - SDK AWS para Python
- **JWT** - Autenticação baseada em tokens

## Como Usar

### Pré-requisitos
- Conta AWS com acesso aos serviços: Lambda, SES, S3 e SQS
- Python 3.8 ou superior
- Boto3 instalado

### Configuração da Função de Notificação
1. Crie templates de e-mail no Amazon SES
2. Configure uma fila SQS como trigger para a função Lambda
3. As mensagens devem seguir o formato:
   ```json
   {
     "receiver_email": "destinatario@exemplo.com",
     "sender_email": "remetente@exemplo.com", 
     "template_name": "nome_do_template",
     "placeholders": { 
       "chave1": "valor1",
       "chave2": "valor2"
     }
   }
   ```

### Configuração da Função de URLs Pré-assinadas
1. Configure a variável de ambiente `BUCKET_NAME` com o nome do bucket S3
2. Configure um autorizador JWT no API Gateway
3. O endpoint retornará um URL pré-assinado válido por 1 hora

## Estrutura do Projeto
```
hackathon-lambda/
│
├── notification/        # Função Lambda para notificações via e-mail
│   ├── main.py          # Código principal
│   └── requirements.txt # Dependências
│
└── presigned/           # Função Lambda para geração de URLs pré-assinadas
    └── lambda_function.py # Código principal
```

## Implantação

Para implantar as funções Lambda:

1. Configure suas credenciais AWS
2. Prepare o pacote de implantação para cada função
3. Faça upload do código para o AWS Lambda
4. Configure os triggers e permissões necessárias

## Testes


```bash
python -m unittest discover
```
