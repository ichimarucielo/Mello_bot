from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
import pytest
pytest.skip("SharePoint test skipped due to authentication issues", allow_module_level=True)

# resto do arquivo...

SITE_URL = "https://cielo-my.sharepoint.com/personal/feborges_cielo_com_br"

USERNAME = "feborges@cielo.com.br"
PASSWORD = "Maria060860."

ctx = ClientContext(SITE_URL).with_credentials(
    UserCredential(USERNAME, PASSWORD)
)

web = ctx.web
ctx.load(web)
ctx.execute_query()

print(f"Conectado: {web.properties['Title']}")