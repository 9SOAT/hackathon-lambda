import json
import pytest
from lambda_pre_sign_up import lambda_handler

def test_adiciona_email_nos_claims_do_token():
    # Arrange
    evento = {
        "request": {
            "userAttributes": {
                "email": "usuario@exemplo.com"
            }
        }
    }

    # Act
    resultado = lambda_handler(evento, None)

    # Assert
    assert resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['claimsToAddOrOverride']['email'] == "usuario@exemplo.com"

def test_preserva_dados_originais_do_evento():
    # Arrange
    evento = {
        "request": {
            "userAttributes": {
                "email": "usuario@exemplo.com",
                "nome": "Nome do Usuário"
            },
            "outrosDados": {
                "origem": "aplicativo"
            }
        }
    }

    # Act
    resultado = lambda_handler(evento, None)

    # Assert
    assert resultado["request"]["userAttributes"]["email"] == "usuario@exemplo.com"
    assert resultado["request"]["userAttributes"]["nome"] == "Nome do Usuário"
    assert resultado["request"]["outrosDados"]["origem"] == "aplicativo"

def test_erro_quando_email_nao_fornecido():
    # Arrange
    evento = {
        "request": {
            "userAttributes": {}
        }
    }

    # Act & Assert
    with pytest.raises(KeyError):
        lambda_handler(evento, None)

def test_estrutura_completa_da_resposta():
    # Arrange
    evento = {
        "request": {
            "userAttributes": {
                "email": "usuario@exemplo.com"
            }
        }
    }

    # Act
    resultado = lambda_handler(evento, None)

    # Assert
    assert 'response' in resultado
    assert 'claimsAndScopeOverrideDetails' in resultado['response']
    assert 'idTokenGeneration' in resultado['response']['claimsAndScopeOverrideDetails']
    assert 'accessTokenGeneration' in resultado['response']['claimsAndScopeOverrideDetails']
    assert 'claimsToAddOrOverride' in resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']
    assert 'claimsToSuppress' in resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']
    assert 'scopesToAdd' in resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']
    assert 'scopesT`Suppress' in resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']
    assert 'groupOverrideDetails' in resultado['response']['claimsAndScopeOverrideDetails']

def test_verificar_erro_no_nome_do_campo():
    # Este teste verifica o campo com erro de digitação
    # Arrange
    evento = {
        "request": {
            "userAttributes": {
                "email": "usuario@exemplo.com"
            }
        }
    }

    # Act
    resultado = lambda_handler(evento, None)

    # Assert
    # O campo deveria ser 'scopesToSuppress', mas está como 'scopesT`Suppress' no código
    assert 'scopesT`Suppress' in resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']

def test_arrays_vazios_nos_campos_de_listas():
    # Arrange
    evento = {
        "request": {
            "userAttributes": {
                "email": "usuario@exemplo.com"
            }
        }
    }

    # Act
    resultado = lambda_handler(evento, None)

    # Assert
    assert resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['claimsToSuppress'] == []
    assert resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToAdd'] == []
    assert resultado['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesT`Suppress'] == []
