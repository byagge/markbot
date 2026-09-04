from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    admin_ids: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    bot_username: str = "PeterRateBot"
    welcome_sticker_id: str = ""
    database_path: str = "data/bot.db"

    # Optional MTProto user account (gifts + username resolution)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_session: str = ""

    # Premium custom emoji IDs (from @PremiumEmoji)
    emoji_fire: str = ""
    emoji_trophy: str = ""
    emoji_star: str = ""
    emoji_people: str = ""
    emoji_question: str = ""
    emoji_back: str = ""
    emoji_share: str = ""
    emoji_refresh: str = ""
    emoji_swords: str = ""
    emoji_globe: str = ""
    emoji_gift: str = ""
    emoji_letters: str = ""
    emoji_chart: str = ""
    emoji_search: str = ""
    emoji_sparkles: str = ""
    emoji_picture: str = ""
    emoji_memo: str = ""
    emoji_hourglass: str = ""
    emoji_speech: str = ""
    emoji_warning: str = ""
    emoji_bulb: str = ""
    emoji_megaphone: str = ""
    emoji_check: str = ""
    emoji_tools: str = ""
    emoji_loudspeaker: str = ""
    emoji_chart_up: str = ""
    emoji_green: str = ""
    emoji_gold: str = ""
    emoji_silver: str = ""
    emoji_bronze: str = ""
    emoji_point_down: str = ""
    emoji_user: str = ""
    emoji_medal: str = ""
    emoji_handshake: str = ""
    emoji_party: str = ""
    emoji_cross: str = ""
    emoji_plus: str = ""
    emoji_bullet: str = ""
    emoji_home: str = ""

    @property
    def admins(self) -> set[int]:
        if not self.admin_ids.strip():
            return set()
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

    @property
    def bot_username_clean(self) -> str:
        return self.bot_username.lstrip("@")


settings = Settings()
