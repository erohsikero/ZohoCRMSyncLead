from zcrmsdk.src.com.zoho.crm.api.user_signature import UserSignature
from zcrmsdk.src.com.zoho.api.authenticator.store import FileStore
from zcrmsdk.src.com.zoho.api.logger import Logger
from zcrmsdk.src.com.zoho.crm.api.initializer import Initializer
from zcrmsdk.src.com.zoho.api.authenticator.oauth_token import OAuthToken, TokenType
from zcrmsdk.src.com.zoho.crm.api.sdk_config import SDKConfig
from CADataCenter import CADataCenter
import os

def initialize_sdk():
    logger = Logger.get_instance(Logger.Levels.INFO, "./sdk_log.log")
    user = UserSignature(os.getenv('ZOHO_USER_EMAIL'))

    environment = CADataCenter.PRODUCTION()
    print("Environment Created:", environment)
    token = OAuthToken(
        client_id=os.getenv('ZOHO_CLIENT_ID'),
        client_secret=os.getenv('ZOHO_CLIENT_SECRET'),
        token=os.getenv('ZOHO_TOKEN'),
        token_type=TokenType.REFRESH,
        redirect_url=os.getenv('ZOHO_REDIRECT_URL'),
    )
    print("Token Generated:", token)
    store = FileStore(file_path="./zoho_sdk_tokens.txt")

    config = SDKConfig(
        auto_refresh_fields=True,
        pick_list_validation=False
    )

    resource_path = "./zoho_resources"

    Initializer.initialize(
        user=user,
        environment=environment,
        token=token,
        store=store,
        sdk_config=config,
        resource_path=resource_path,
        logger=logger
    )

initialize_sdk()