from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes,
    ConversationHandler, CallbackQueryHandler
)
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Подключение к PostgreSQL
Base = declarative_base()
engine = create_engine("postgresql://tariff_db_g7eb_user:K73qHQVHxpqF5SM71Li3OzhVblBNlmve@dpg-d1digvbe5dus73djsp1g-a/tariff_db_g7eb")
Session = sessionmaker(bind=engine)
session = Session()

class Record(Base):
    __tablename__ = "record"
    id = Column(Integer, primary_key=True)
    date = Column(String)
    user = Column(String)
    cur = Column(Float)
    new = Column(Float)
    cost = Column(Float)
    period = Column(Integer)
    payback = Column(String)
    economy = Column(Float)

Base.metadata.create_all(engine)

# Состояния
CUR, NEW, COST, PERIOD = range(4)
CHANNEL_ID = "@F_S_Ta"

# Кнопка для проверки подписки
check_keyboard = InlineKeyboardMarkup(
    [[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]]
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Чтобы использовать бота, подпишитесь на канал:\nhttps://t.me/F_S_Ta\n\n"
        "После этого нажмите кнопку ниже 👇",
        reply_markup=check_keyboard
    )
    return ConversationHandler.END  # пока не начинаем диалог

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await query.message.reply_text("✅ Подписка подтверждена! Введите текущий тариф (₽/мес):")
            return await cur_entry_from_callback(update, context)
        else:
            raise Exception("Not subscribed")
    except:
        await query.message.reply_text(
            "🚫 Вы не подписались на канал. Пожалуйста, подпишитесь и нажмите кнопку ещё раз.",
            reply_markup=check_keyboard
        )
        return ConversationHandler.END

# Начинаем опрос после подписки
async def cur_entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()  # очищаем предыдущие данные на всякий случай
    context.user_data["from_callback"] = True
    return CUR

# Опрос
async def cur_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['cur'] = float(update.message.text)
    await update.message.reply_text("Введите новый тариф:")
    return NEW

async def new_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new'] = float(update.message.text)
    await update.message.reply_text("Введите стоимость подключения:")
    return COST

async def cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['cost'] = float(update.message.text)
    await update.message.reply_text("Введите период в годах:")
    return PERIOD

async def period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cur = context.user_data['cur']
    new = context.user_data['new']
    cost = context.user_data['cost']
    period = float(update.message.text)
    months = int(period * 12)
    cumulative_old, cumulative_new = 0, cost
    payback = None
    for m in range(1, months + 1):
        cumulative_old += cur
        cumulative_new += new
        if payback is None and cumulative_old - cumulative_new >= 0:
            payback = m
    payback_text = str(payback) if payback else "Не достигнута"
    economy = round(cumulative_old - cumulative_new)
    rec = Record(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        user=update.effective_user.full_name,
        cur=cur, new=new, cost=cost,
        period=months, payback=payback_text, economy=economy
    )
    session.add(rec)
    session.commit()
    await update.message.reply_text(f"Окупаемость: {payback_text} мес.\nЭкономия: {economy}₽")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token("8134172809:AAFydCkI2T32hYxL6y8zCVlTdp_lrL7hY18").build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, cur_tariff)],
        states={
            CUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, cur_tariff)],
            NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_tariff)],
            COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, cost)],
            PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, period)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_sub"))
    app.add_handler(conv_handler)
    app.run_polling()
    
