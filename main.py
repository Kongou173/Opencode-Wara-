import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import pytz
from datetime import datetime, timedelta
import asyncio
import random
from keep_alive import keep_alive
from gemini_chat import gemini_chat
from dotenv import load_dotenv
from akinator_python import Akinator
import wikipedia
import requests 

# 環境変数の読み込み
load_dotenv("./lol/.env")

# 環境変数の取得
TOKEN = os.getenv("DISCORD_TOKEN")
SUPPORT_SERVER_URL = os.getenv("SUPPORT_SERVER_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Botの初期設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # banやkickで必要

bot = commands.Bot(command_prefix="!", intents=intents)
synced = False  # コマンドの同期フラグ

# 会話履歴を保存する変数（グローバルに設定）
conversation_history = []

# ステータス表示（presence）
@tasks.loop(seconds=20)
async def presence_loop():
    game = discord.Game("/help - Bot Help")
    await bot.change_presence(activity=game)

# Bot起動時の処理
@bot.event
async def on_ready():
    global synced
    if not synced:
        await bot.tree.sync()  # スラッシュコマンドの同期
        synced = True
    print(f"Logged in as {bot.user.name}")
    presence_loop.start()

# /help コマンド：利用可能なコマンド一覧を表示
@bot.tree.command(name="help", description="利用可能なコマンド一覧を表示します")
async def bot_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ボットの使い方",
        color=discord.Colour.blurple()
    ).add_field(name="/help", value="利用可能なコマンド一覧を表示します") \
     .add_field(name="/ban <user>", value="ユーザーをBANします") \
     .add_field(name="/kick <user>", value="ユーザーをキックします") \
     .add_field(name="/timeout <user> <duration>", value="指定された時間だけユーザーをタイムアウトします (1分〜1時間)") \p
     .add_field(name="/support", value="サポートサーバーのリンクを表示します") \
     .add_field(name="/say <message>", value="Botが指定メッセージを代わりに話します") \
     .add_field(name="/time", value="現在の時刻を表示します") \
     .add_field(name="/chat <message>", value="Gemini APIとチャット") \
     .add_field(name="/chat_clear", value="チャット履歴を削除します") \
     .add_field(name="/random", value="ユーザー名をランダムに変更します") \
　　　.add_field(name="/wiki", value="Wikipediaから情報を取得します") \
　　　.add_field(name="/proggles", value="今年の残り日数を表示します") \
     .add_field(name="/joke", value="ランダムでジョークを表示します")
    await interaction.response.send_message(embed=embed)

        title="サポートサーバーリンク",
        description=SUPPORT_SERVER_URL, # 直接リンクを表示
        color=discord.Colour.blue()  # 埋め込みの色を設定
    )
    await interaction.response.send_message(embed=embed)




# /ban コマンド：ユーザーをBAN
@bot.tree.command(name="ban", description="ユーザーをBANします")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} をBANしました。")
    else:
        await interaction.response.send_message("BAN権限がありません。", ephemeral=True)

# /kick コマンド：ユーザーをキック
@bot.tree.command(name="kick", description="ユーザーをキックします")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member.mention} をキックしました。")
    else:
        await interaction.response.send_message("キック権限がありません。", ephemeral=True)

#timeout コマンド：ユーザーをタイムアウト
@bot.tree.command(name="timeout", description="指定時間だけユーザーをタイムアウトします")
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: int):
    if interaction.user.guild_permissions.moderate_members:
        if 1 <= duration <= 60:
            timeout_duration = discord.utils.utcnow() + timedelta(minutes=duration)
            await member.timeout(timeout_duration)
            await interaction.response.send_message(f"{member.mention} を {duration} 分間タイムアウトしました。")
        else:
            await interaction.response.send_message("タイムアウトの時間は1分〜60分の範囲で指定してください。", ephemeral=True)
    else:
        await interaction.response.send_message("タイムアウト権限がありません。", ephemeral=True)

# /say コマンド：Botが代わりに話す
@bot.tree.command(name="say", description="Botが指定メッセージを代わりに話します")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)

# /time コマンド：現在の時刻を東京タイムゾーンで表示
@bot.tree.command(name="time", description="現在の時刻（東京/JST）を表示します")
async def show_time(interaction: discord.Interaction):
    tokyo_tz = pytz.timezone("Asia/Tokyo")
    current_time = datetime.now(tokyo_tz).strftime("%Y-%m-%d %H:%M:%S JST")
    await interaction.response.send_message(f"現在の時刻（東京/JST）: {current_time}")
    
#/chatコマンド:Geminiとチャット
@bot.tree.command(name="chat", description="Geminiとチャットします")
async def chat(interaction: discord.Interaction, message: str):
    global conversation_history
    await interaction.response.defer()  # 処理中であることをユーザーに通知

    # チャット履歴にメッセージを追加
    conversation_history.append(message)

    try:
        # Gemini APIにメッセージを送信（非同期処理）
        response = await asyncio.to_thread(gemini_chat, message)

        # Gemini APIからのレスポンスを送信
        await interaction.followup.send(response)

    except Exception as e:
        # エラーメッセージをユーザーに送信
        await interaction.followup.send(f"エラーが発生しました: {str(e)}")

# /chat_clear コマンド：チャット履歴を削除
@bot.tree.command(name="chat_clear", description="チャット履歴を削除します")
async def clear_chat(interaction: discord.Interaction):
    global conversation_history
    conversation_history.clear()  # 会話履歴をクリア
    await interaction.response.send_message("チャット履歴を削除しました。")
@bot.tree.command(
    name="random",
    description="ランダムにあなたの名前を変更します"
)
async def random_name(interaction: discord.Interaction):
    random_names = [
        "受験面倒くさいンゴ…", 
        "やべぇなw", 
        "我はねんねこ信者", 
        "鯖主つおい", 
        "ねんねこには勝てん", 
        "誰か助けてクレメンスw",
        "やばい…いつになったら約束の地に行けるんだ…",
        "鯖主は東方projectの博麗霊夢が推しですw",
        "反ねんねこは滅ぶべし"
        
    ]
    new_name = random.choice(random_names)  # ランダムで名前を選ぶ
    try:
        # 実行したユーザーのニックネームを変更
        await interaction.user.edit(nick=new_name)
        await interaction.response.send_message(f"あなたの新しい名前は「{new_name}」です!")
    except discord.Forbidden:
        await interaction.response.send_message("名前を変更できませんでした。Botに権限があるか確認してください。")
    except discord.HTTPException:
        await interaction.response.send_message("名前を変更する際にエラーが発生しました。")
        
# OpenWeatherMap APIを利用した天気情報取得
@bot.tree.command(name="weather", description="指定した都市の天気情報を取得します")
async def get_weather(interaction: discord.Interaction, city: str, forecast: bool = False):
    """
    city: 都市名
    forecast: Trueなら5日間の天気予報を取得、Falseなら現在の天気
    """
    await interaction.response.defer()  # 処理中メッセージを表示

    # APIエンドポイント
    if forecast:
        url = f"http://api.openweathermap.org/data/2.5/forecast"
    else:
        url = f"http://api.openweathermap.org/data/2.5/weather"

    # APIリクエスト
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",  # 温度を摂氏で取得
        "lang": "ja",       # 日本語対応
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # HTTPエラーをチェック
        data = response.json()

        if forecast:
            embed = discord.Embed(
                title=f"🌦️ {city} の5日間天気予報",
                color=discord.Colour.blue()
            )
            # 3時間ごとの予報を取得
            for forecast in data["list"][:10]:  # 最大10件まで表示
                dt = datetime.fromtimestamp(forecast["dt"]).strftime("%Y-%m-%d %H:%M:%S")
                weather = forecast["weather"][0]["description"]
                temp = forecast["main"]["temp"]
                embed.add_field(
                    name=f"{dt}",
                    value=f"天気: {weather}, 温度: {temp}℃",
                    inline=False
                )
        else:
            # 現在の天気
            weather = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            icon = data["weather"][0]["icon"]
            icon_url = f"http://openweathermap.org/img/wn/{icon}@2x.png"

            embed = discord.Embed(
                title=f"☀️ {city} の現在の天気",
                description=f"天気: {weather}\n温度: {temp}℃\n湿度: {humidity}%\n風速: {wind_speed} m/s",
                color=discord.Colour.orange()
            )
            embed.set_thumbnail(url=icon_url)

        await interaction.followup.send(embed=embed)
    except requests.exceptions.HTTPError as e:
        await interaction.followup.send(f"エラー: 指定された都市「{city}」の天気情報が見つかりません。")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {str(e)}")
        
# Wikipedia APIを使用した検索コマンド
@bot.tree.command(name="wiki", description="Wikipediaから情報を取得します")
async def wiki(interaction: discord.Interaction, query: str):
    await interaction.response.defer()  # 処理中メッセージを表示
    try:
        wikipedia.set_lang("ja")  # Wikipediaの言語を日本語に設定
        summary = wikipedia.summary(query, sentences=2)  # 要約を取得
        page_url = wikipedia.page(query).url  # ページURLを取得
        embed = discord.Embed(
            title=f"Wikipedia: {query}",
            description=summary,
            color=discord.Colour.green()
        ).add_field(name="詳細リンク", value=f"[こちら]({page_url})")
        await interaction.followup.send(embed=embed)
    except wikipedia.exceptions.DisambiguationError as e:
        await interaction.followup.send(f"曖昧なキーワードです。次の候補から選択してください: {', '.join(e.options[:5])}...")
    except wikipedia.exceptions.PageError:
        await interaction.followup.send("指定されたキーワードのページが見つかりませんでした。")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {str(e)}")

# サーバー情報を表示するコマンド
@bot.tree.command(name="server", description="サーバーの情報を表示します")
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title=f"サーバー情報: {guild.name}",
        color=discord.Colour.blue()
    )
    embed.add_field(name="サーバー名", value=guild.name, inline=False)
    embed.add_field(name="サーバーID", value=guild.id, inline=False)
    embed.add_field(name="メンバー数", value=guild.member_count, inline=False)
    embed.add_field(name="オーナー", value=str(guild.owner), inline=False)
    embed.add_field(name="サーバー作成日", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await interaction.response.send_message(embed=embed)

# アキネーターゲームを開始するコマンドを追加
@bot.tree.command(name="akinator", description="アキネーターと遊びます")
async def akinator(interaction: discord.Interaction):
    await interaction.response.send_message("アキネーターを開始します。質問に答えてください！")
    
    # Akinatorのインスタンスを作成してゲームを開始
    akinator = Akinator()
    akinator.start_game()
    
    # ゲームの進行
    while True:
        try:
            # 質問を表示
            question = akinator.question
            await interaction.followup.send(question)
            
            # ユーザーからの入力を待機
            response = await bot.wait_for('message', check=lambda m: m.author == interaction.user)
            answer = response.content.lower()
            
            # 「戻る」機能
            if answer == 'b':
                akinator.go_back()
            else:
                # 回答をアキネーターに送信
                akinator.post_answer(answer)
                
                # 正解が出た場合
                if akinator.answer_id:
                    result = f"{akinator.name} / {akinator.description}"
                    await interaction.followup.send(f"アキネーターの答えは: {result}")
                    
                    # 正解かどうか確認
                    await interaction.followup.send("これは正しいですか？ (y/n)")
                    confirmation = await bot.wait_for('message', check=lambda m: m.author == interaction.user)
                    if confirmation.content.lower() == 'y':
                        await interaction.followup.send("ゲーム終了！ありがとうございました！")
                        break
                    elif confirmation.content.lower() == 'n':
                        akinator.exclude()
                else:
                    await interaction.followup.send("答えが分かりませんでした。再試行します。")
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")
            break

@bot.tree.command(name="search", description="Google検索結果を取得します")
async def search(interaction: discord.Interaction, query: str):
    """
    query: 検索キーワード
    """
    await interaction.response.defer()  # 処理中メッセージを表示

    # Google Custom Search APIのURL
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": query,

@bot.tree.command(name="proggles", description="今年の残り日数を表示します。")
async def proggles(interaction: discord.Interaction):
    today = datetime.now()
    end_of_year = datetime(today.year, 12, 31)
    remaining_days = (end_of_year - today).days + 1

    await interaction.response.send_message(f"今年はあと **{remaining_days}日** しか残っていないよ！")

@bot.tree.command(name="joke", description="プログラマーに関するジョークをランダムに表示します")
async def joke(interaction: discord.Interaction):
    # ランダムでジョークを選択する
    selected_joke = random.choice(jokes)
    # ジョークをチャットで返信する
    await interaction.response.send_message(selected_joke)

# ジョークのリスト
jokes = [
    "Q: プログラマーがPythonを選ぶ理由は？\nA: ヘビのようにコードがスッと書けるから！",
    "Q: プログラマーはなぜ怒ると怖い？\nA: ポインタでメモリを指し示すように、怒りの矛先を一点に集中させるから！",
    "Q: プログラマーの恋人との会話でよく出てくる言葉は？\nA: 「あー…ちょっと待っててくんない？バグを直すから」",
    "Q: プログラマーが「簡単だよ」と言っているコードを見た時の一般の人の心境は？\nA: 騙されてはいけない…これは罠だ…",
    "Q: プログラマーが「アルゴリズム」と言っている時、一般人が何を連想する？\nA: 魔法の言葉",
    "Q: プログラマーが「オブジェクト指向」と言っている時、一般の人は何を思う？\nA: なぁにそれぇ？",
    "Q: プログラマーが最も嫌いな言葉は？\nA: 「もちろんちゃんと動くよね？」「バグはないね？」",
    "Q: プログラマーはなぜ猫を飼う人が多いのか？\nA: えー…静かな環境でコードを書けるから…と思ってるのが1つ目で、2つ目は猫もコードを書けるんじゃないかと思っているから。",
    "Q: プログラマーが最も恐れるものは？\nA: デッドラインと、上司からの「明日までにこの機能追加してくんない？」",
    "Q: プログラマーが「おっ！これ簡単そうじゃんwちょっとやってみようかな。もちろん自分でやるよ。」と言った時、聞いてた周囲が思う事は？\nA: ああ…また徹夜だよ…",
    "Q: プログラマーが「正規表現」と言っている時、一般人が何を連想する？\nA: 呪文",
    "Q: プログラマーが「よし、完成した！完璧だな…ふっ…自分が怖いぜ…」と思った瞬間、必ず起こることは？\nA: バグが出現",
    "Q: プログラマーが「あ、ちょっと直すだけだから。」と言ったあと、数時間後に現れた時の定番のセリフは？\nA: 「ちょっとバグが複雑で…」",
    "このジョークには何分の一の確率で、とある物が出てきます。",
    "このbotの開発者のおすすめの曲は、White Letter、初音ミクさんの心境、stardust dreams、Whose Eye is This Anyway、琥珀色の街、上海蟹の朝、I'm a mess、ピースサイン、メサイア、サウダージです！",
    "幻想郷に行きたいねぇ…",
    "Q: コードレビュー中にプログラマーが最も恐れるセリフは？\nA: A: 「あのさ。このコード、誰が書いたのか教えて？」",   
    "Q: コードレビュー中に最もよく耳にする言葉は？\nA: 「ここの部分は、もう少しシンプルに書けますよ」「ここの変数、分かりづらいですね。もう少しわかりやすく書いた方がいいんじゃないですか？」",
    
]

@bot.tree.command(name="omikuji", description="おみくじを引いて今日の運勢を占おう！(1日1回まで)")
async def omikuji(interaction: discord.Interaction):
    user_id = interaction.user.id
    current_time = datetime.now()

    # ユーザーがすでにおみくじを引いている場合
    if user_id in omikuji_data:
        last_time = omikuji_data[user_id]
        if current_time.date() == last_time.date():
            await interaction.response.send_message("今日はすでにおみくじを引いています！また明日試してね。", ephemeral=True)
            return

    # おみくじ結果をランダムで選ぶ
    result = random.choice(list(omikuji_results.keys()))
    details = omikuji_results[result]

    # ユーザーの引いた時間を記録
    omikuji_data[user_id] = current_time

    # 結果メッセージの作成
    response = f"🎋 **{interaction.user.name}のおみくじ** 🎋\n\n"
    response += f"**運勢**: {result}\n"
    response += f"**和歌**: {details['和歌']}\n"
    response += f"**願望**: {details['願望']}\n"
    response += f"**健康**: {details['健康']}\n"
    response += f"**待ち人**: {details['待ち人']}\n"
    response += f"**出産**: {details['出産']}\n"
    response += f"**商売**: {details['商売']}\n"
    response += f"**投稿**: {details['投稿']}"

    # 結果を送信
    await interaction.response.send_message(response)
    omikuji_data = {}

# おみくじ結果と詳細データ
omikuji_results = {
    "大吉": {
        "和歌": "思ひつつ 寝ればや人の 見えつらむ\n夢と知りせば 覚めざらましを",
        "願望": "焦る事ない　機は来る",
        "健康": "普通",
        "待ち人": "気まぐれに現れる",
        "出産": "支えが必要",
        "商売": "無理しない方が良い",
        "投稿": "様子見で"
    },
    "小吉": {
        "和歌": "君がため 春の野に出でて 若菜摘む\n我が衣手に 雪は降りつつ",
        "願望": "少しずつ進展",
        "健康": "小さいトラブルに注意",
        "待ち人": "近くにいるかも",
        "出産": "無難",
        "商売": "まずまず",
        "投稿": "控えめに"
    },
    "末吉": {
        "和歌": "忘れじの 行末までは 難ければ\n今日を限りの 命ともがな",
        "願望": "まだ時間がかかる",
        "健康": "過信は禁物",
        "待ち人": "遅い",
        "出産": "心構えが必要",
        "商売": "時期を見て動く",
        "投稿": "様子見で"
    },
    "凶": {
        "和歌": "世の中は 常にもがもな 渚漕ぐ\n海人の小舟の 綱手かなしも",
        "願望": "難しいが諦めない",
        "健康": "気をつけて",
        "待ち人": "期待しすぎない方が良い",
        "出産": "やや困難",
        "商売": "時期が悪い",
        "投稿": "注意が必要"
    },
    "大凶": {
        "和歌": "心にも あらでうき世に ながらへば\n恋しかるべき 夜半の月かな",
        "願望": "ほぼ叶わない",
        "健康": "危険",
        "待ち人": "来ない",
        "出産": "大変な道のり",
        "商売": "諦めるのが吉",
        "投稿": "絶対ダメ"
    }
}

# Botを実行
keep_alive()
bot.run(TOKEN)

# Botを実行
keep_alive()
bot.run(TOKEN)
