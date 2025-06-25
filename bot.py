from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes,
    ConversationHandler, CallbackQueryHandler
)
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import logging

# Логирование
logging.basicConfig(level=logging.INFO)

# --- База данных ---
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

# --- Состояния ---
CUR, NEW, COST, PERIOD = range(4)
CHANNEL_ID = "@F_S_Ta"

# --- Кнопка подписки ---
check_keyboard = InlineKeyboardMarkup(
    [[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]]
)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Чтобы использовать бота, подпишитесь на канал:\n"
        "https://t.me/F_S_Ta\n\n"
        "После подписки нажмите кнопку ниже 👇",
        reply_markup=check_keyboard
    )
    return ConversationHandler.END

# --- Проверка подписки по кнопке ---
async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        logging.info(f"{user_id=} {member.status=}")
        if member.status in ["member", "administrator", "creator"]:
            await context.bot.send_message(user_id, "✅ Подписка подтверждена! Теперь нажмите /calculate для начала расчёта")
        else:
            raise Exception("Not subscribed")
    except Exception as e:
        logging.error(f"Ошибка подписки: {e}")
        await query.message.reply_text(
            "🚫 Вы ещё не подписаны на канал. Подпишитесь и нажмите кнопку снова.",
            reply_markup=check_keyboard
        )

# --- Старт расчёта после подписки ---
async def start_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Введите текущий тариф (₽/мес):")
    return CUR

# --- Пошаговый опрос ---
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

    # Сохраняем в БД
    rec = Record(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        user=update.effective_user.full_name,
        cur=cur, new=new, cost=cost,
        period=months, payback=payback_text, economy=economy
    )
    session.add(rec)
    session.commit()

    await update.message.reply_text(
        f"✅ Расчёт завершён!\n\n"
        f"Окупаемость: {payback_text} мес.\n"
        f"Экономия: {economy}₽"
    )
    return ConversationHandler.END

# --- Отмена ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# --- Запуск приложения ---
if __name__ == '__main__':
    app = ApplicationBuilder().token("8134172809:AAFydCkI2T32hYxL6y8zCVlTdp_lrL7hY18").build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("calculate", start_calculation)
        ],
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
    
