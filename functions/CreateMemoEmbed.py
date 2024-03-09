import discord
from functions.tinyfunctions import probably

def CreateFarmingEmbed():
    embed = discord.Embed(
        title=f"**練等備忘錄**", 
        color=0x6f00d2,
        )
    embed.add_field(name="**__設定類__**", value=f"戰地\n極限屬性\n傳授\nV核心", inline = True)
    embed.add_field(name="**__裝備類__**", value=f"練等裝\n現金裝備\n稱號\n寵物", inline = True)
    embed.add_field(name="", value=f"", inline = False)
    embed.add_field(name="**__消耗類__**", value=f"秘藥\n怪公黃水\n加倍\n追加\n商城加倍", inline = True)
    embed.add_field(name="**__其他類__**", value=f"活動加倍", inline = True)
    embed.set_footer(text="記得確認面板的掉寶楓掉")

    if probably(0.1):        
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/913252189126926397.webp?size=96&quality=lossless')
    else:
        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/918869202876653608/1213116778415132792/02636093.info.icon.png?ex=65f44e0a&is=65e1d90a&hm=77759d9950dc6063e61ae5b52f55d5caaffc27c06d70bfc894f76d62479a2dce&')
    return embed

def CreateCombatEmbed():
    embed = discord.Embed(
        title=f"**打王備忘錄**", 
        color=0x6f00d2,
        )
    embed.add_field(name="**__設定類__**", value=f"戰地\n極限屬性\n傳授\nV核心", inline = True)
    embed.add_field(name="**__裝備類__**", value=f"打王裝\n現金裝備\n稱號\n寵物\n萌獸", inline = True)
    embed.add_field(name="**__技能類__**", value=f"開關技能\n迴響\n稱號\n寵物", inline = True)
    embed.add_field(name="**__消耗類__**", value=f"秘藥\n怪公水\n公會祝福\n戰地卷\n天氣\n提升10階\n其他消耗", inline = True)
    embed.add_field(name="**__其他類__**", value=f"活動BUFF", inline = True)
    embed.set_footer(text="記得確認面板的主屬/B傷/爆傷是否正確")
    
    embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/911319739253522462.webp?size=96&quality=lossless')
    return embed