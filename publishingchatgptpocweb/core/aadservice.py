# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from flask import current_app as app
import msal
import os
from core.config import settings

class AadService:

    def get_access_token():
        '''Generates and returns Access token

        Returns:
            string: Access token
        '''

        response = None
        try:
            if settings.PBI_AUTHENTICATION_MODE.lower() == 'masteruser':

                # Create a public client to authorize the app with the AAD app
                clientapp = msal.PublicClientApplication(settings.PBI_CLIENT_ID, authority=settings.PBI_AUTHORITY_URL)
                accounts = clientapp.get_accounts(username=settings.PBI_USER)

                if accounts:
                    # Retrieve Access token from user cache if available
                    response = clientapp.acquire_token_silent([settings.PBI_SCOPE_BASE], account=accounts[0])

                if not response:
                    # Make a client call if Access token is not available in cache
                    response = clientapp.acquire_token_by_username_password(settings.PBI_USER, settings.PBI_PASSWORD, scopes=[settings.PBI_SCOPE_BASE])     

            # Service Principal auth is the recommended by Microsoft to achieve App Owns Data Power BI embedding
            elif settings.PBI_AUTHENTICATION_MODE.lower() == 'serviceprincipal':
                authority = settings.PBI_AUTHORITY_URL.replace('organizations', settings.PBI_TENANT_ID)
                clientapp = msal.ConfidentialClientApplication(settings.PBI_CLIENT_ID, client_credential=settings.PBI_CLIENT_SECRET, authority=authority)

                # Make a client call if Access token is not available in cache
                response = clientapp.acquire_token_for_client(scopes=['https://analysis.windows.net/powerbi/api/.default'])

            try:
                return response['access_token']
            except KeyError:
                raise Exception(response['error_description'])

        except Exception as ex:
            raise Exception('Error retrieving Access token\n' + str(ex))