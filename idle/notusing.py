'''class IronBrickButton(discord.ui.View): 
      
    @discord.ui.button(style = discord.ButtonStyle.green, emoji='<:meh_ironbrick:1013069551275085824>')
    async def button_callback(self, interaction, button):
        meh_type_dict = {
            1 : '<:meh_1:1013069719940648961>',
            2 : '<:meh_2:1013069722117476395>',
            3 : '<:meh_3:1013069724441128970>',
            4 : '<:meh_4:1013069727280672779>', #-
            5 : '<:meh_5:1013069729436536853>',
            6 : '<:meh_6:1013069731693084692>',
            7 : '<:meh_7:1013069733882495027>',
            8 : '<:meh_8:1013069735837052988>', #-
            9 : '<:meh_9:1013069737934209024>'
        }
        meh_success, meh_brick_cnt, meh_level, meh_brick_cnt_final = use_ironbrick()
        button.label = f'x{meh_brick_cnt}'
        if meh_success :
            if meh_level == 1 :
                await interaction.response.send_message(content=f'{interaction.user}在第{meh_brick_cnt_final}次失敗後獲得了**滅龍騎士盔甲**<:meh_9:1013069737934209024>')
            else:
                button_successorfail = [x for x in self.children if x.custom_id == 'successorfail'][0]
                button_successorfail.label = '成功!!!'
                await interaction.response.edit_message(content=f'{meh_type_dict[meh_level]}', view=self)
        else:
            button_successorfail = [x for x in self.children if x.custom_id == 'successorfail'][0]
            button_successorfail.label = '失敗!!!'
            await interaction.response.edit_message(content=f'{meh_type_dict[meh_level]}',view=self)

    @discord.ui.button(label = ' ', style = discord.ButtonStyle.gray, disabled = True, custom_id='successorfail', emoji='<:stand:1013144996498657330>')
    async def button_callback_successorfail(self, interaction, button):
        await interaction.response.send_message(content=f'失敗!!!')'''


'''# 敲鐵塊       
    if message.content == '<:meh_9:1013069737934209024>' or message.content == '<:meh_ironbrick:1013069551275085824>':    
        if message.channel.id in prizechannelblacklist:
            await message.channel.send(f'請到<#578080016634609664>進行')
        else:        
            view = IronBrickButton()
            await message.channel.send(f'<:meh_1:1013069719940648961>', view=view)  ''' 

'''
meh_brick_cnt = 0
meh_brick_cnt_final = 0
meh_level = 1


def use_ironbrick():
    global meh_brick_cnt
    global meh_level
    global meh_brick_cnt_final
    meh_chance_dcit = {
            1 : 0.5,
            2 : 0.25,
            3 : 0.1,
            5 : 0.05,
            6 : 0.02,
            7 : 0.005
        }
    meh_brick_cnt += 1 
    if probably(meh_chance_dcit[meh_level]):
        meh_success = True 
        if meh_level == 3 or meh_level == 7:
            meh_level += 2
        else:
            meh_level += 1 

        if meh_level == 9:
            meh_level = 1
            meh_brick_cnt_final = meh_brick_cnt
            meh_brick_cnt = 0
    else:
        meh_success = False
    return meh_success, meh_brick_cnt, meh_level, meh_brick_cnt_final'''