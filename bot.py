await generate_and_send_reports(
        cur=context.user_data['cur'],
        new=context.user_data['new'],
        cost=context.user_data['cost'],
        period_years=context.user_data['period'],
        user_name=update.effective_user.full_name,
        bot=context.bot,
        chat_id=update.effective_chat.id,
        admin_id=ADMIN_ID
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Расчёт отменён.')
    return ConversationHandler.END

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.full_name
    if not os.path.exists(HISTORY_FILE):
        await update.message.reply_text("История пуста.")
        return
    wb_src = load_workbook(HISTORY_FILE)
    ws_src = wb_src.active
    wb_user = Workbook()
    ws_user = wb_user.active
    ws_user.title = "История"
    ws_user.append([cell.value for cell in ws_src[1]])
    for row in ws_src.iter_rows(min_row=2, values_only=True):
        if row[1] == user_name:
            ws_user.append(row)
    if ws_user.max_row == 1:
        await update.message.reply_text("У вас пока нет расчётов.")
        return
    buf = BytesIO()
    wb_user.save(buf)
    buf.seek(0)
    await update.message.reply_document(buf, filename="моя_история.xlsx")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Доступные команды:\n"
        "/start - Начать расчет тарифа\n"
        "/cancel - Отменить текущий ввод\n"
        "/history - Показать вашу историю расчетов\n"
        "/help - Показать это сообщение"
    )
    await update.message.reply_text(help_text)

if name == 'main':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, cur_tariff)],
            NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_tariff)],
            COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, cost)],
            PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, period)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()
