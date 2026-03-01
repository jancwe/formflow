from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class SmbConfig(BaseModel):
    enabled: bool
    server: str
    share: str
    folder: str
    username: str
    password: str

class CompanyConfig(BaseModel):
    name: str
    address: str
    logo_filename: str

class ColorsConfig(BaseModel):
    primary: str
    text_dark: str
    text_light: str
    bg_light: str

class AppSettings(BaseSettings):
    """Main application settings model, loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_prefix='APP_',
        env_nested_delimiter='__',
        env_file=".env", 
        env_file_encoding='utf-8', 
        extra='ignore'
    )

    company: CompanyConfig
    colors: ColorsConfig
    smb: SmbConfig