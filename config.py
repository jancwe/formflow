from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class SmbConfig(BaseModel):
    enabled: bool = False
    server: str | None = None
    share: str | None = None
    folder: str = ""
    username: str | None = None
    password: str | None = None

class CompanyConfig(BaseModel):
    name: str = "Musterfirma GmbH"
    address: str = "Musterstraße 123 &bull; 12345 Musterstadt"
    logo_filename: str = "logo.png"

class ColorsConfig(BaseModel):
    primary: str = "#0056b3"
    text_dark: str = "#32373c"
    text_light: str = "#6d6d6d"
    bg_light: str = "#fdfdfd"

class AppSettings(BaseSettings):
    """Main application settings model, loaded from environment variables."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    company: CompanyConfig = Field(default_factory=CompanyConfig)
    colors: ColorsConfig = Field(default_factory=ColorsConfig)
    smb: SmbConfig = Field(default_factory=SmbConfig)

