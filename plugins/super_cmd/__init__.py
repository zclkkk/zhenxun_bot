from nonebot import on_command
from nonebot.permission import SUPERUSER
from models.level_user import LevelUser
from nonebot.typing import T_State
from nonebot.adapters import Bot, Event
from nonebot.rule import to_me
from util.utils import get_message_at, get_message_text, is_number, get_bot
from services.log import logger
from .data_source import open_remind, close_remind
from models.group_info import GroupInfo
from models.friend_user import FriendUser


__plugin_name__ = '超级用户指令 [Hidden]'
__plugin_usage__ = '用法'


super_cmd = on_command("添加管理", aliases={'删除管理', '添加权限', '删除权限'}, rule=to_me(), priority=1, permission=SUPERUSER, block=True)
oc_gb = on_command('开启广播通知', aliases={'关闭广播通知'}, rule=to_me(), permission=SUPERUSER, priority=1, block=True)
cls_group = on_command("所有群组", rule=to_me(), permission=SUPERUSER, priority=1, block=True)
cls_friend = on_command("所有好友", rule=to_me(), permission=SUPERUSER, priority=1, block=True)
del_group = on_command('退群', rule=to_me(), permission=SUPERUSER, priority=1, block=True)
update_group_info = on_command('更新群信息', rule=to_me(), permission=SUPERUSER, priority=1, block=True)
update_friend_info = on_command('更新好友信息', rule=to_me(), permission=SUPERUSER, priority=1, block=True)
# update_cmd = on_command('更新命令开关', rule=to_me(), permission=SUPERUSER, priority=1, block=True)


@super_cmd.handle()
async def _(bot: Bot, event: Event, state: T_State):
    try:
        args = get_message_text(event.json()).strip().split(" ")
        qq = int(get_message_at(event.json())[0])
        if state["_prefix"]["raw_command"][:2] == "添加":
            level = int(args[0])
            if await LevelUser.set_level(qq, event.group_id, level, 1):
                result = "添加管理成功, 权限: " + str(level)
            else:
                result = "管理已存在, 更新权限: " + str(level)
        else:
            if await LevelUser.delete_level(qq, event.group_id):
                result = "删除管理成功!"
            else:
                result = "该账号无管理权限!"
        await super_cmd.send(result)
    except Exception as e:
        await super_cmd.send("执行指令失败!")
        logger.error(f'执行指令失败 e{e}')


@oc_gb.handle()
async def _(bot: Bot, event: Event, state: T_State):
    group = get_message_text(event.json())
    if group:
        if is_number(group):
            group = int(group)
            for g in await bot.get_group_list():
                if g['group_id'] == group:
                    break
            else:
                await oc_gb.finish('没有加入这个群...', at_sender=True)
            # try:
            if state["_prefix"]["raw_command"] == '开启广播通知':
                logger.info(f'USER {event.user_id} 开启了 GROUP {group} 的广播')
                await oc_gb.finish(await open_remind(group, 'gb'), at_sender=True)
            else:
                logger.info(f'USER {event.user_id} 关闭了 GROUP {group} 的广播')
                await oc_gb.finish(await close_remind(group, 'gb'), at_sender=True)
            # except Exception as e:
            #     await oc_gb.finish(f'关闭 {group} 的广播失败', at_sender=True)
        else:
            await oc_gb.finish('请输入正确的群号', at_sender=True)
    else:
        await oc_gb.finish('请输入要关闭广播的群号', at_sender=True)


@del_group.handle()
async def _(bot: Bot, event: Event, state: T_State):
    group = get_message_text(event.json())
    if group:
        if is_number(group):
            try:
                await bot.set_group_leave(group_id=int(group))
                logger.info(f'退出群聊 {group} 成功')
                await del_group.finish(f'退出群聊 {group} 成功', at_sender=True)
            except Exception as e:
                logger.info(f'退出群聊 {group} 失败 e:{e}')
        else:
            await del_group.finish(f'请输入正确的群号', at_sender=True)
    else:
        await del_group.finish(f'请输入群号', at_sender=True)


@cls_group.handle()
async def _(bot: Bot, event: Event, state: T_State):
    gl = await bot.get_group_list(self_id=bot.self_id)
    msg = ["{group_id} {group_name}".format_map(g) for g in gl]
    msg = "\n".join(msg)
    msg = f"bot:{bot.self_id}\n| 群号 | 群名 | 共{len(gl)}个群\n" + msg
    await bot.send_private_msg(self_id=bot.self_id, user_id=int(list(bot.config.superusers)[0]), message=msg)


@cls_friend.handle()
async def _(bot: Bot, event: Event, state: T_State):
    gl = await bot.get_friend_list(self_id=bot.self_id)
    msg = ["{user_id} {nickname}".format_map(g) for g in gl]
    msg = "\n".join(msg)
    msg = f"| QQ号 | 昵称 | 共{len(gl)}个好友\n" + msg
    await bot.send_private_msg(self_id=bot.self_id, user_id=int(list(bot.config.superusers)[0]), message=msg)


@update_group_info.handle()
async def _(bot: Bot, event: Event, state: T_State):
    bot = get_bot()
    gl = await bot.get_group_list(self_id=bot.self_id)
    gl = [g['group_id'] for g in gl]
    num = 0
    rst = ''
    for g in gl:
        group_info = await bot.get_group_info(group_id=g)
        if await GroupInfo.add_group_info(group_info['group_id'], group_info['group_name'],
                                          group_info['max_member_count'], group_info['member_count']):
            num += 1
            logger.info(f'自动更新群组 {g} 信息成功')
        else:
            logger.info(f'自动更新群组 {g} 信息失败')
            rst += f'{g} 更新失败\n'
    await update_group_info.send(f'成功更新了 {num} 个群的信息\n{rst[:-1]}')


@update_friend_info.handle()
async def _(bot: Bot, event: Event, state: T_State):
    num = 0
    rst = ''
    fl = await get_bot().get_friend_list(self_id=bot.self_id)
    for f in fl:
        if await FriendUser.add_friend_info(f['user_id'], f['nickname']):
            logger.info(f'自动更新好友 {f["user_id"]} 信息成功')
            num += 1
        else:
            logger.warning(f'自动更新好友 {f["user_id"]} 信息失败')
            rst += f'{f["user_id"]} 更新失败\n'
    await update_friend_info.send(f'成功更新了 {num} 个好友的信息\n{rst[:-1]}')


# @update_cmd.handle()
# async def _(bot: Bot, event: Event, state: T_State):
#     gl = await bot.get_group_list(self_id=bot.self_id)
#     gl = [g['group_id'] for g in gl]
#     for g in gl:
#         check_group_switch_json(g)
#     for file in os.listdir(DATA_PATH + 'group_help'):
#         os.remove(DATA_PATH + f'group_help/{file}')
#     await update_cmd.finish('更新命令完成！', at_sender=True)





