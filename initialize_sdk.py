from zcrmsdk.src.com.zoho.crm.api.dc.us_data_center import USDataCenter
from zcrmsdk.src.com.zoho.crm.api.user_signature import UserSignature
from zcrmsdk.src.com.zoho.api.authenticator.store import FileStore
from zcrmsdk.src.com.zoho.api.logger import Logger
from zcrmsdk.src.com.zoho.crm.api.initializer import Initializer
from zcrmsdk.src.com.zoho.api.authenticator.oauth_token import OAuthToken, TokenType
from zcrmsdk.src.com.zoho.crm.api.sdk_config import SDKConfig
from CADataCenter import CADataCenter
import os
from dotenv import load_dotenv


load_dotenv()

class ZohoSDKInitializer:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ZohoSDKInitializer, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._initialize_sdk()
    
    def _initialize_sdk(self):
        """Initialize the Zoho SDK with configuration"""
        logger = Logger.get_instance(Logger.Levels.INFO, "./sdk_log.log")
        userEmail = os.getenv('ZOHO_USER_EMAIL')
        print("User Email:", userEmail)
        user = UserSignature(userEmail)

        # environment = CADataCenter.PRODUCTION()
        environment = USDataCenter.PRODUCTION()
        print("Environment Created:", environment)
        # Initialize OAuth token
        clientId = os.getenv('ZOHO_CLIENT_ID')
        clientSecret = os.getenv('ZOHO_CLIENT_SECRET')
        token = os.getenv('ZOHO_REFRESH_TOKEN')
        redirectUrl = os.getenv('ZOHO_REDIRECT_URL')
        token = OAuthToken(
            client_id=clientId,
            client_secret=clientSecret,
            token=token,
            token_type=TokenType.REFRESH,
            redirect_url=redirectUrl,
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
        print("Zoho SDK initialized successfully")
    
    def get_instance(self):
        """Return the singleton instance"""
        return self
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)"""
        cls._instance = None
        cls._initialized = False


# Backward compatibility function
def initialize_sdk():
    """Initialize the Zoho SDK (singleton pattern)"""
    return ZohoSDKInitializer()


# Convenience function to get the initialized instance
def get_sdk_instance():
    """Get the initialized SDK instance"""
    return ZohoSDKInitializer()