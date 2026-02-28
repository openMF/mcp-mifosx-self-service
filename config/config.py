import os
from dotenv import load_dotenv

load_dotenv()


BASE_URL = os.getenv("MIFOS_BASE_URL", "https://tt.mifos.community")
API_BASE_PATH = "/fineract-provider/api/v1"
DEFAULT_TENANT = os.getenv("MIFOS_TENANT", "default")
