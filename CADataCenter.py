try:
    from zcrmsdk.src.com.zoho.crm.api.dc.data_center import DataCenter
except Exception as e:
    from zcrmsdk.src.com.zoho.crm.api.dc.data_center import DataCenter


class CADataCenter(DataCenter):
    """
    This class represents the properties of Zoho CRM in the Canada (CA) domain.
    """

    @classmethod
    def PRODUCTION(cls):
        """
        Zoho CRM Production environment in Canada domain.
        """
        return DataCenter.Environment(
            "https://www.zohoapis.ca",
            cls().get_iam_url(),
            cls().get_file_upload_url()
        )

    @classmethod
    def SANDBOX(cls):
        """
        Zoho CRM Sandbox environment in Canada domain.
        """
        return DataCenter.Environment(
            "https://sandbox.zohoapis.ca",
            cls().get_iam_url(),
            cls().get_file_upload_url()
        )

    @classmethod
    def DEVELOPER(cls):
        """
        Zoho CRM Developer environment in Canada domain.
        """
        return DataCenter.Environment(
            "https://developer.zohoapis.ca",
            cls().get_iam_url(),
            cls().get_file_upload_url()
        )

    def get_iam_url(self):
        return "https://accounts.zohocloud.ca/oauth/v2/token"

    def get_file_upload_url(self):
        return "https://content.zohoapis.com"
