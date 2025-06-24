# Lambda Function
resource "aws_lambda_function" "presigned_url_lambda" {
  function_name = "${var.projectName}_presigned_url"
  filename      = "lambda_function.zip"
  source_code_hash = filebase64sha256("lambda_function.zip")
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  role          = aws_iam_role.lambda_exec_role.arn

  environment {
    variables = {
      BUCKET_NAME = "presigned-url-fiap-test"
    }
  }
}