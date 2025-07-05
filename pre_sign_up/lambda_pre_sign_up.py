import json

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event))
    event['response'] = {
        "claimsAndScopeOverrideDetails": {
            "idTokenGeneration": {},
            "accessTokenGeneration": {
                "claimsToAddOrOverride": {
                    "email": event["request"]["userAttributes"]["email"]
                },
                "claimsToSuppress": [],
                "scopesToAdd": [],
                "scopesT`Suppress": []
            },
            "groupOverrideDetails": {}
        }
    }
    return event