from datetime import datetime
import asyncio
import logging
from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import DevelopmentConfig, ProductionConfig
from database import GameCategory, GameOption, Video, db, User, GameHistory, init_db, migrate
from telegram.ext import ContextTypes
from flask_cors import CORS
import os
from asgiref.wsgi import WsgiToAsgi



logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

asgi_app = WsgiToAsgi(app)


env = os.getenv('FLASK_ENV', 'development')
TOKEN="8064622273:AAHi_B_PQQMcjRbJr3jmmZJ7dO-9MXrL0PI"

if env == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)


db.init_app(app)


# db = SQLAlchemy(app)
migrate = Migrate(app, db)

CORS(app, resources={r"/render-webhook":{"origins" : "*"}})

ADMIN_IDS = [6687026573]




async def set_bot_commands(application):
    commands = [
    BotCommand("start", "Start interacting with the bot"),
    BotCommand("play_game", "Play a game"),
    BotCommand("watch_video", "Watch a video to earn tokens"),
    BotCommand("view_history", "View your game history"),
    BotCommand("get_user_id", "to get my user id")
    ]
    await application.bot.set_my_commands(commands)

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def handle_text(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logging.info('handle_text triggered')

    if context.user_data.get('awaiting_video_name'):
        video_name = update.message.text
        context.user_data['video_name'] = video_name
        context.user_data['awaiting_video_name'] = False

        await update.message.reply_text(f"Video name '{video_name}' captured. Please enter the video link:")
        context.user_data['awaiting_video_link'] = True
        return
    
    if context.user_data.get('awaiting_video_link'):
        video_link = update.message.text
        video_name = context.user_data.get('video_name')

        with app.app_context():
            new_video = Video(video_name=video_name, video_link=video_link)
            db.session.add(new_video)
            db.session.commit()
        await update.message.reply_text(f"Video '{video_name}' with the link '{video_link}' has been set successfully.")
        context.user_data['awaiting_video_link'] = False
        context.user_data['video_name'] = None
        return

    if context.user_data.get('awaiting_category_name'):
        await capture_game_category(update, context)
    elif context.user_data.get('awaiting_options'):
        await capture_options(update, context)
    elif context.user_data.get('edit_category_id'):
        await capture_new_category_name(update, context)
    elif context.user_data.get('edit_option_id'):
        await capture_new_option_name(update, context)
    else:
        logging.info("No active state. Ignoring message")

async def get_user_id(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"your teelgram user id is: {user_id}")

async def start(update: Update, context:ContextTypes.DEFAULT_TYPE):
    logging.info("start command reached")
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    try:
        with app.app_context():
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                new_user = User(telegram_id=user_id, name=user_name)
                db.session.add(new_user)
                db.session.commit()
    except Exception as e:
        logging.error(f"Database error: {e}")
        await update.message.reply_text("Error interacting with the database")
        
        # video_link = user.video_link if user.video_link else None
        # video_name = user.video_name if user.video_name else None

    keyboard = [
        [InlineKeyboardButton("Play Game", callback_data="play_game")],
        [InlineKeyboardButton("Watch Video (Get Token)", callback_data="watch_video")],
        [InlineKeyboardButton("View Result", url="https://www.youtube.com/watch?v=live_draw_link")],
        [InlineKeyboardButton("View History", callback_data="view_history")]
    ]

    # if video_link and video_name:
    #     keyboard.insert(1, [InlineKeyboardButton(f"Watch {video_name} (Get Token)", url=video_link)])
    

    

    # show admin options to admins
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("Admin: Add Game category", callback_data="add_game_category")])
        keyboard.append([InlineKeyboardButton("Admin: add game options", callback_data="add_category_option")])
        keyboard.append([InlineKeyboardButton("Admin: Set Video Link", callback_data="set_video_link")])
        keyboard.append([InlineKeyboardButton("Admin: list all categories and options", callback_data="list_categories_and_options")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    with app.app_context():
        # user = User.query.filter_by(telegram_id=user_id).first()
        # if not user:
        #     new_user = User(telegram_id=user_id, name=user_name)
        #     db.session.add(new_user)
        #     db.session.commit()

        user_tokens = User.query.filter_by(telegram_id=user_id).first().tokens
    
    logging.info(f"Sending message to {user_name}")
    await update.message.reply_text(f"hello {user_name} welcome to Nameofname!, you have {user_tokens} game tokens.", reply_markup=reply_markup)

async def add_game_category(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("You are not authorized to add games.", show_alert=True)
        return
    

    await query.message.reply_text("Please enter the new game category name:")
    context.user_data['awaiting_category_name'] = True

async def capture_game_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("capture_game_category triggered")

    if context.user_data.get('awaiting_category_name'):
        category_name = update.message.text 

        with app.app_context():
            # Check if the category already exists
            existing_category = GameCategory.query.filter_by(name=category_name).first()
            if existing_category:
                await update.message.reply_text(f"Category '{category_name}' already exists.")
            else:
                # Add the new category
                new_category = GameCategory(name=category_name)
                db.session.add(new_category)
                db.session.commit()
                await update.message.reply_text(f"New game category '{category_name}' has been added.")
        
        # Reset the state
        context.user_data['awaiting_category_name'] = False



async def add_category_option(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("You are not authorized to add options.", show_alert=True)
        return
    
    with app.app_context():
        categories = GameCategory.query.all()
        if not categories:
            await query.message.reply_text("No categories available. Please add a category first.")
            return
    keyboard = [[InlineKeyboardButton(c.name, callback_data=f"add_option_{c.id}")] for c in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("choose a category to add options to:", reply_markup=reply_markup)
    # context.user_data['awaiting_category_name_for_options'] = True

async def category_selected_for_options(update:Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("category_selected_for_options triggered")
    query = update.callback_query
    category_id = int(query.data.split('_')[2])

    context.user_data['selected_category_id'] = category_id
    context.user_data['awaiting_options'] = True

    logging.info(f"category_selected_for_options awaiting options set to true for category {category_id}")

    await query.message.reply_text("Please enter the options to add, separated by commas:")


async def capture_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("capture_options triggered")

    
    # If we are waiting for the options to be input
    if context.user_data.get('awaiting_options'):
        options_input = update.message.text
        logging.info(f"Received options input: {options_input}")
        options = [opt.strip() for opt in options_input.split(",")]  # Split the options by commas and remove extra spaces

        logging.info(f"Parsed options: {options}")
        category_id = context.user_data.get('selected_category_id')

        logging.info(f"Selected Category ID: {category_id}")

        if not category_id:
            await update.message.reply_text("Error: Category ID not found.")
            logging.error("Category ID misssing whn trying to save options")
            return

        # Add the options to the category in the database
        with app.app_context():
            category = GameCategory.query.filter_by(id=category_id).first()
            if category:
                for option in options:
                    new_option = GameOption(option=option, category_id=category.id)
                    db.session.add(new_option)
                db.session.commit()
                
                await update.message.reply_text(f"Options '{', '.join(options)}' have been added to category '{category.name}'.")

        # Reset the state after processing
        context.user_data['awaiting_options'] = False
        context.user_data['selected_category_id'] = None
    else:
        logging.info("Not awaiting options, ignoring message.")

async def category_selected(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    category_id = int(query.data.split('_')[1])
    data = query.data

    # if data.startswith("category_"):
    #     category_id = int(data.split('_')[1])
    with app.app_context():
        category = GameCategory.query.filter_by(id=category_id).first()

        if not category:
            await query.message.reply_text(f"Category not found.")
            return
        options = category.options
        if options:
            keyboard = [[InlineKeyboardButton(option.option, callback_data=f"option_{option.id}")] for option in options]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(f"Pick an option from {category.name}:", reply_markup=reply_markup)
        else:
            await query.message.reply_text(f"No options found in category '{category.name}'.")
   
    
# async def capture_category_name_for_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if context.user_data.get('awaiting_category_name_for_options'):
#         category_name = update.message.text
#         context.user_data['category_name'] = category_name

#         # Check if the category exists in the database
#         with app.app_context():
#             category = GameCategory.query.filter_by(name=category_name).first()
#             if not category:
#                 await update.message.reply_text(f"Category '{category_name}' does not exist. Please add the category first or choose an existing one.")
#                 context.user_data['awaiting_category_name_for_options'] = False  # Stop waiting for a category name
#                 return
        
#         await update.message.reply_text(f"Category '{category_name}' found. Now, please enter the options you want to add, separated by commas:")
#         context.user_data['awaiting_options'] = True  # Set flag to wait for options
#         context.user_data['awaiting_category_name'] = False




          
            

    #         options = category.options
    #         if not options:
    #             await query.message.reply_text(f"No options found in category '{category.name}'.")
    #             return
        
    #         keyboard = [[InlineKeyboardButton(option.option, callback_data=f"option_{option.id}")] for option in options]
    #         reply_markup = InlineKeyboardMarkup(keyboard)

    #         await query.message.reply_text(f"Pick an option from {category.name}:", reply_markup=reply_markup)

    # else:
    #     await query.message.reply_text("Invalid category selection.")

   

    # selected_numbers = "1,2,3,4,5,6"
 
    # keyboard = [[InlineKeyboardButton(option.option, callback_data=f"option_{option.id}")] for option in options]
    # reply_markup = InlineKeyboardMarkup(keyboard)

    # await query.message.reply_text(f"Pick 6 from {category}:", reply_markup=reply_markup)

async def option_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    option_id = int(query.data.split('_')[1])

    if 'selected_options' not in context.user_data:
        context.user_data['selected_options'] = []

    context.user_data['selected_options'].append(option_id)

    if len(context.user_data['selected_options']) >=6:
        with app.app_context():
            user = User.query.filter_by(telegram_id=user_id).first()
            selected_options = context.user_data['selected_options']

            game_history = GameHistory(user_id=user.id, category="Some Category", selections=", ".join(map(str, selected_options)))   
            db.session.add(game_history)
            db.session.commit()

            user.tokens -= 1
            db.session.commit()

            await query.message.reply_text(f"Game played! Selections: {', '.join(map(str, selected_options))}")
            context.user_data['selected_options'] = []

    else:
        await query.answer(f"Option selected. You have selected {len(context.user_data['selected_options'])}/6 options.") 

    # with flask_app.app_context():
    #     option = GameOption.query.filter_by(id=option_id).first()
    #     if option:
    #         await query.message.reply_text(f"You selected: {option.option}")
    #     else:
    #         await query.message.reply_text(f"Option not found.")

    # data = query.data
    # if data.startswith("option_"):
    #     try:
    #         option_id = int(data.split('_')[1])

    #         with flask_app.app_context():
    #             option = GameOption.query.filter_by(id=option_id).first()
    #             if option:
    #                 await query.message.reply_text(f"You selected: {option.option}")
    #             else:
    #                 await query.message.reply_text(f"Option not found.")
    #     except (ValueError, IndexError):
    #         logging.error("Error processing option callback.")
    #         await query.message.reply_text("Invalid option selection.")
    # else:
    #     await query.message.reply_text("Invalid option callback.")



async def set_video_link(update:Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("You are not authorized to set video links.", show_alert=True)
        return
    
    await query.message.reply_text("Admin action: Set video name - Feature here.")
    context.user_data['awaiting_video_name'] = True

# async def capture_video_name(update:Update, context:ContextTypes.DEFAULT_TYPE):
#     if context.user_data.get('awaiting_video_name'):
#         video_name = update.mesage.text
#         context.user_data['video_name'] = video_name

#         await update.message.reply_text(f"Video name '{video_name}' captured. Please enter the video link:")
#         context.user_data['awaiting_video_name'] = False
#         context.user_data['awaiting_video_link'] = True

# async def capture_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if context.user_data.get('awaiting_video_link'):
#         video_link = update.message.text
#         video_name = context.user_data.get('video_name')

#         with flask_app.app_context():
#             user_id = update.effective_user.id
#             user = User.query.filter_by(telegram_id=user_id).first()

#             if user:
#                 user.video_name = video_name
#                 user.video_link = video_link
#                 db.session.commit()
        
#         await update.message.reply_text(f"Video '{video_name}' with link has saved successfully")
#         context.user_data['awaiting_video_link'] = False
#         context.user_data['video_name'] = None

def get_user_tokens(user_id):
    with app.app_context():
        user = User.query.filter_by(telegram_id=user_id).first()
        if user:
            return user.tokens
        else:
            return None

async def watch_video(update: Update, context: ContextTypes.DEFAULT_TYPE ):
    query = update.callback_query
    user_id = query.from_user.id

    with app.app_context():
        videos = Video.query.all()

        if not videos:
            await query.message.reply_text("No video available to watch.")
            return

        keyboard = []

    # Display the button with the video name
        for video in videos:
            video_link = video.video_link

            if not video_link.startswith("https://"):
                video_link = f"https://{video_link}"

            keyboard.append([InlineKeyboardButton(video.video_name, web_app=WebAppInfo(url=video_link))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "select a video to watch and earn tokens:",
        reply_markup=reply_markup
    )
    
    # query = update.callback_query
    # user_id = query.from_user.id

    # web_app_url = "https://adgramtemplate.vercel.app"

    # keyboard = [
    #     [InlineKeyboardButton("Ad", web_app=WebAppInfo(url=web_app_url))]
    # ]
    # reply_markup = InlineKeyboardMarkup(keyboard)

    # await query.message.reply_text(
    #     "Click the button below to watch an ad and earn a token.",
    #     reply_markup=reply_markup
    # )

@app.route('/adsgram_callback', methods=['POST', 'OPTIONS'])
def adsgram_callback():
    logging.info(f"Received {request.method} request at /adsgram_callback")

    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response

    data = request.get_json()
    logging.info(f"Received callback data: {data}")
    user_id = data.get('user_id')

    if user_id:
        user_id_int = int(user_id)

        logging.info(f"User ID {user_id_int} is being credited with a token.")
        with app.app_context():
            user = User.query.filter_by(telegram_id = user_id_int).first()
            if user:
                user.tokens += 1
                db.session.commit()
                return jsonify({'status': 'success', 'tokens': user.tokens}), 200

            else:
                logging.error("User not found in database.")
                return jsonify({'status': 'error', 'message': 'user not found'}), 404

    else:
        logging.error("User ID was not provided in the request.")
        return jsonify({'status': 'error', 'message': 'user id not provided'}), 400



async def play_game(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id

    with app.app_context():
        user = User.query.filter_by(telegram_id=user_id).first()

        if not user:
            await query.message.reply_text("user not found")
            return
    
    user_tokens = user.tokens

        
    if user_tokens < 1:
        await query.answer("You don't have enough tokens to play! Watch a video to earn tokens.", show_alert=True) 
    # start the game play process
    else:
        with app.app_context():
            categories = GameCategory.query.all()
            if not categories:
                await query.message.reply_text("No game categories available.")
                return

        keyboard = [[InlineKeyboardButton(c.name, callback_data=f"category_{c.id}")] for c in categories]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text('Choose a category:', reply_markup=reply_markup)

    with app.app_context():
        user.tokens -= 1
        db.session.commit()




        

async def save_game(user_id, category, selections):
    with app.app_context():
        user = User.query.filter_by(telegram_id=user_id).first()
        if user:
            # Save the game in history
            game_history = GameHistory(user_id=user.id, category=category, selections=", ".join(selections))

            db.session.add(game_history)
            user.tokens -= 1
            db.session.commit()

    logging.info(f"Game saved for user {user_id} in category {category} with selections {selections}")


async def view_history(update: Update, context):

    query = update.callback_query
    user_id = query.from_user.id
    

    with app.app_context():
        user = User.query.filter_by(telegram_id=user_id).first()

        if user:
            history = GameHistory.query.filter_by(user_id=user.id).all()

            if len(history) == 0:
                # Show popup for no game history
                await query.answer("No game history found.", show_alert=True)
            else:
                # Format the history with date and time
                formatted_history = "\n".join([
                    f"Category: {g.category}, Options: {g.selections}, Played at: {g.played_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    for g in history
                ])
                await query.message.reply_text(f"Your game history:\n{formatted_history}")

async def list_categories_and_options(update:Update, context:ContextTypes.DEFAULT_TYPE):
    logging.info("list and categories")
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("you are not authorized to view categories and options")
        return

    with app.app_context():
        categories = GameCategory.query.all()

        if not categories:
            await update.message.reply_text("no categories found")
            return

        category_list = []
        keyboard = []
        for category in categories:
            options = ", ".join([option.option for option in category.options])
    
            category_list.append(f"category: {category.name}\nOptions: {options if options else 'no options available'}")

            keyboard.append([InlineKeyboardButton(f"Edit {category.name}", callback_data=f"edit_category_{category.id}"),
             InlineKeyboardButton(f"Delete {category.name}", callback_data=f"delete_category_{category.id}")])
        
            for option in category.options:
                keyboard.append([InlineKeyboardButton(f"Edit {option.option}", callback_data=f"edit_option_{option.id}"),
                InlineKeyboardButton(f"delete {option.option}", callback_data=f"delete_option_{option.id}")
                                ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("\n\n".join(category_list), reply_markup=reply_markup)

async def edit_category(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    category_id = int(query.data.split('_')[2])

    context.user_data['edit_category_id'] = category_id

    await query.message.reply_text(f"Please enter the new name for category ID {category_id}")

async def capture_new_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category_id = context.user_data.get('edit_category_id')
    new_name = update.message.text

    if category_id:
        with app.app_context():
            category = GameCategory.query.filter_by(id=category_id).first()
            if category:
                category.name = new_name
                db.session.commit()
                await update.message.reply_text(f"Category updated to {new_name}")
            else:
                await update.message.reply_text("Category not found.")
        context.user_data.pop('edit_category_id', None)
    else:
        await update.message.reply_text("No category found to edit")


async def delete_category(update:Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    category_id = int(query.data.split('_')[2])

    with app.app_context():
        category = GameCategory.query.filter_by(id=category_id).first()

        if category:
            db.session.delete(category)
            db.session.commit()
            await query.message.reply_text(f"Category {category.name} deleted.")
        else:
            await query.message.reply_text("category not found")

async def edit_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    option_id = int(query.data.split('_')[2])

    context.user_data['edit_option_id'] = option_id
    await query.message.reply_text(f"Please enter the new name for option ID {option_id}:")

async def capture_new_option_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    option_id = context.user_data.get('edit_option_id')
    new_name = update.message.text

    if option_id:
        with app.app_context():
            option = GameOption.query.filter_by(id=option_id).first()
            if option:
                option.option = new_name
                db.session.commit()
                await update.message.reply_text(f"Option updated to {new_name}")
            else:
                await update.message.reply_text("Option not found.")
        context.user_data.pop('edit_option_id', None)
    else:
        await update.message.reply_text("No option found to edit.")

    
async def delete_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    option_id = int(query.data.split('_')[2])

    # Delete the option
    with app.app_context():
        option = GameOption.query.filter_by(id=option_id).first()
        if option:
            db.session.delete(option)
            db.session.commit()
            await query.message.reply_text(f"Option {option.option} deleted.")
        else:
            await query.message.reply_text("Option not found.")


async def set_webhook(application):
    webhook_url = os.getenv('WEBHOOK_URL', 'https://telegram-lotto-bot.onrender.com')

    try:
        await application.bot.set_webhook(webhook_url)
        logging.info(f"Webhook set successfully to {webhook_url}")
    except telegram.error.TimedOut as e:
        logging.error(f"Error setting webhook: {e}")


@app.route('/render-webhook', methods=['POST'])
def webhook_handler():
    json_data = request.get_json(force=True)
    logging.info(f"Received webhook: {json_data}")
    update = Update.de_json(json_data, application.bot)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.process_update(update))

    # asyncio.run(application.process_update(update))
    return 'ok'

@app.route('/')
def index():
    return "bot is running"

async def post_init(application):
    await set_bot_commands(application)

def main():
    global application
    with app.app_context():
        init_db()
    application = (ApplicationBuilder().token(TOKEN).connect_timeout(60).read_timeout(60).post_init(post_init).build())

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(list_categories_and_options, pattern="list_categories_and_options"))
    # application.add_handler(CommandHandler("get_user_id", get_user_id))
    application.add_handler(CallbackQueryHandler(add_game_category, pattern="add_game_category"))
    application.add_handler(CallbackQueryHandler(add_category_option, pattern="add_category_option"))
    application.add_handler(CallbackQueryHandler(category_selected_for_options, pattern="^add_option_"))

    # play, watch, history
    application.add_handler(CallbackQueryHandler(play_game, pattern="play_game"))
    application.add_handler(CallbackQueryHandler(watch_video, pattern="watch_video"))

    application.add_handler(CallbackQueryHandler(option_selected, pattern="^option_"))

    application.add_handler(CallbackQueryHandler(category_selected, pattern="^category_"))

    application.add_handler(CallbackQueryHandler(view_history, "view_history"))

    application.add_handler(CallbackQueryHandler(set_video_link, pattern="set_video_link"))

    application.add_handler(CallbackQueryHandler(edit_category, pattern="edit_category_"))
    application.add_handler(CallbackQueryHandler(delete_category, pattern="delete_category_"))
    application.add_handler(CallbackQueryHandler(edit_option, pattern="edit_option_"))
    application.add_handler(CallbackQueryHandler(delete_option, pattern="delete_option_"))
                                                 

    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, capture_options))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    if env == 'production':
        logging.info("Running in production mode, setting webhook")
        asyncio.run(set_webhook(application))
        # Serve the Flask app
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
         # In development, use polling
        logging.info("Running in development mode, using polling")
        application.run_polling()

    

    # asyncio.get_event_loop().run_until_complete(set_webhook(application))

    # asyncio.run(set_webhook(application))

    # await set_bot_commands(application)
    # start

    # adding options

  



    # application.add_handler(CommandHandler("history", view_history))

    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(set_webhook(application))

    # application.run_polling()

    # application.run_polling()
    # app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, capture_category_name_for_option))


if __name__ == '__main__':
    main()
    # application.run_polling()