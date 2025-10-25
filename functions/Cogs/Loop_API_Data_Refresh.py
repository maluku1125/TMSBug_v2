import datetime
import asyncio
from discord.ext import commands, tasks
from functions.API_functions.API_Request_Character import refresh_all_expired_character_data

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def get_now_YMDHMS():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

timezone = datetime.timezone(datetime.timedelta(hours=8))


class Loop_API_Data_Refresh(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f"{get_now_YMDHMS()}, Data Refresh Loop initializing...")
        self.API_AllData_Refresh.start()

    def cog_unload(self):
        self.API_AllData_Refresh.cancel()
        print(f"{get_now_YMDHMS()}, API Data Refresh Loop stopped")
    
    # Official use - Execute at specific time daily
    @tasks.loop(time=datetime.time(hour=2, minute=15, tzinfo=timezone))  # Set to 2:00 for testing

    async def API_AllData_Refresh(self):
        """Execute database refresh task every Monday at 2:15 AM"""
        print(f"{get_now_YMDHMS()}, 🚀 Starting API all character data refresh...")

        try:
            # Execute refresh task, refresh data older than 7 days
            stats = refresh_all_expired_character_data(refresh_days=7)
            
            # Output statistics
            print(f"{get_now_YMDHMS()}, 🎉 API all data refresh completed!")
            print(f"Total records: {stats['total_records']}")
            print(f"Fresh records: {stats['fresh_records']}")
            print(f"Expired records: {stats['expired_records']}")
            print(f"Successfully refreshed: {stats['successfully_refreshed']}")
            print(f"Failed refreshes: {stats['failed_refreshes']}")
            print(f"Error records: {stats['error_records']}")
            print("-" * 50)
            
        except Exception as e:
            print(f"{get_now_YMDHMS()}, 💥 Error during API all data refresh: {e}")
            import traceback
            traceback.print_exc()
            print("-" * 50)

