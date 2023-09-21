# Authentication Using Azure Active Directory

import msal
import uuid
from flask import url_for, session
from core.config import settings

class Auth:

    def __init__(self):
        self.AzureAd_TenantId: str = settings.AzureAd_TenantId
        self.AzureAd_ClientId: str = settings.AzureAd_ClientId
        self.AzureAd_ClientSecret: str =  settings.AzureAd_ClientSecret 
        self.AzureAd_Redirect_Path: str = settings.AzureAd_Redirect_Path 
        self.AzureAd_Authority: str = settings.AzureAd_Authority

    def load_cache(self):
        cache = msal.SerializableTokenCache()
        if session.get("token_cache"):
            cache.deserialize(session["token_cache"])
        return cache

    def save_cache(self, cache):
        if cache.has_state_changed:
            session["token_cache"] = cache.serialize()

    def build_msal_app(self,cache=None, authority=None):
        return msal.ConfidentialClientApplication(
            self.AzureAd_ClientId,
            authority=authority or self.AzureAd_Authority,
            client_credential=self.AzureAd_ClientSecret,
            token_cache=cache)

    def build_auth_url(self, authority=None, scopes=None, state=None, to_go=None):
        return self.build_msal_app(authority=authority).get_authorization_request_url(
            scopes or [],
            state=state or str(uuid.uuid4()),
            redirect_uri=url_for("authorize", _external=True))