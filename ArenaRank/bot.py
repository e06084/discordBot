import discord
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import json

# 加载环境变量
load_dotenv()

# 设置 Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def fetch_lm_arena_rankings():
    try:
        print("开始获取排行榜数据...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 访问网页
            await page.goto("https://lmarena.ai/?leaderboard", wait_until="networkidle")
            print("页面加载完成")
            
            # 等待数据加载
            await page.wait_for_selector("table", timeout=30000)
            print("找到表格元素")
            
            # 获取排行榜数据
            rankings = []
            rows = await page.query_selector_all("table tr")
            
            # 跳过表头，获取前10名
            for i, row in enumerate(rows[1:11], 1):
                try:
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 3:
                        model = await cells[1].text_content()
                        score = await cells[2].text_content()
                        rankings.append(f"#{i} {model.strip()} - 分数: {score.strip()}")
                        print(f"解析到数据: #{i} {model.strip()} - {score.strip()}")
                except Exception as e:
                    print(f"解析行 {i} 时出错: {e}")
                    continue
            
            await browser.close()
            print(f"成功获取到 {len(rankings)} 条排名数据")
            return rankings
            
    except Exception as e:
        print(f"获取排行榜时出错: {e}")
        import traceback
        print(traceback.format_exc())
        return []

@bot.event
async def on_ready():
    print(f'{bot.user} 已成功登录!')
    update_rankings.start()

@tasks.loop(hours=24)
async def update_rankings():
    channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
    channel = bot.get_channel(channel_id)
    
    if channel:
        print("开始定时更新排行榜...")
        rankings = await fetch_lm_arena_rankings()
        if rankings:
            embed = discord.Embed(
                title="LM Arena 排行榜更新",
                description="以下是当前前10名的模型排名：",
                color=discord.Color.blue()
            )
            
            rankings_text = "\n".join(rankings)
            embed.add_field(name="排名", value=rankings_text, inline=False)
            
            await channel.send(embed=embed)
            print("排行榜更新已发送")
        else:
            print("获取排行榜失败，本次更新跳过")

@bot.command(name='rankings')
async def get_rankings(ctx):
    try:
        print(f"收到rankings命令 - 来自用户: {ctx.author}")
        await ctx.send("正在获取排行榜数据，请稍候...")
        
        rankings = await fetch_lm_arena_rankings()
        if rankings:
            embed = discord.Embed(
                title="LM Arena 排行榜",
                description="以下是当前前10名的模型排名：",
                color=discord.Color.blue()
            )
            
            rankings_text = "\n".join(rankings)
            embed.add_field(name="排名", value=rankings_text, inline=False)
            
            await ctx.send(embed=embed)
            print("排行榜数据已发送")
        else:
            await ctx.send("获取排行榜数据时出现错误，请稍后再试。")
    except Exception as e:
        print(f"处理rankings命令时出错: {e}")
        await ctx.send(f"执行命令时出现错误: {str(e)}")

# 运行 bot
bot.run(os.getenv('DISCORD_TOKEN')) 