from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, Job, JobQueue
import datetime
from mysql.connector import connect, Error

root_password = '<your root password>'
token = '<your bot token>'

def to_format(text: str, start: datetime.date, end: datetime.date) -> dict:
    return {'text': text, 'start': start, 'end': end}


def task_str(values):
    return str(values['start']) + ' ===== ' + str(values['end']) + '\n' + values['text']


def change_query(query: str, vars=()) -> None:
    with connect(host="localhost", user='root', password=root_password, database='test2') as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, vars)
            connection.commit()


def show_query(query: str) -> list:
    with connect(host="localhost", user='root', password=root_password, database='test2') as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            res = []
            for line in cursor:
                res.append(line)
            return res


def get_info(update: Update, context: CallbackContext) -> None:
    text = 'I am a bot. I can remind you about your tasks.\n' \
           'You can write:\n' \
           '/add <start date> <end date> <description> to add a new task\n' \
           '/delete <number> to delete one of your tasks\n' \
           '/watch to watch all your tasks\n' \
           '/watch <date> to watch all your tasks in definite day\n' \
           '/watch <start date> <end date> to watch your tasks that get into the range' \
           'date format: 2021-07-30'
    update.message.reply_text(text)


def add_task(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 3:
        update.message.reply_text("Wrong count of parameters")
        return
    try:
        if datetime.date.fromisoformat(context.args[0]) > datetime.date.fromisoformat(context.args[1]):
            update.message.reply_text("The start can't be after the end")
            return
    except Exception:
        update.message.reply_text("Wrong date format")
        return
    task = to_format(' '.join(context.args[2:]), datetime.date.fromisoformat(context.args[0]), datetime.date.fromisoformat(context.args[1]))
    if '`' in task['text']:
        update.message.reply_text("You can't use ` character")
        return
    change_query("insert into actions (user_id, text, start, end) values (%s, %s, %s, %s)", (update.message.chat_id, task['text'], task['start'], task['end']))
    update.message.reply_text('Add successful')


def delete_task(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 1:
        update.message.reply_text('Wrong count of parameters')
        return
    if not context.args[0].isnumeric():
        update.message.reply_text('The first parameter should be a positive number')
        return
    task_id = int(context.args[0]) - 1
    chat_id = update.message.chat_id
    tasks = show_query(f"select * from actions where user_id = '{chat_id}'")
    if task_id < 0 or task_id >= len(tasks):
        update.message.reply_text("You haven't the task that has this id")
        return
    del_id = tasks[task_id][0]
    change_query(f"delete from actions where id = '{del_id}'")
    update.message.reply_text("Delete successful")


def print_list(data: list, update: Update, context: CallbackContext) -> None:
    for i in range(len(data)):
        task = to_format(*data[i][2:5])
        update.message.reply_text(str(i + 1) + '.\n' + task_str(task))
    if not data:
        update.message.reply_text('It is empty here now')


def watch(update: Update, context: CallbackContext) -> None:
    if not len(context.args):
        print_list(show_query(f"select * from actions where user_id = {update.message.chat_id}"), update, context)
    elif len(context.args) == 1:
        try:
            datetime.date.fromisoformat(context.args[0])
        except Exception:
            update.message.reply_text('Wrong date format')
            return
        date = datetime.date.fromisoformat(context.args[0])
        print_list(show_query(f"select * from actions where user_id = {update.message.chat_id} and start <= '{date}' and end >= '{date}'"), update, context)
    elif len(context.args) == 2:
        try:
            datetime.date.fromisoformat(context.args[0])
            datetime.date.fromisoformat(context.args[1])
        except Exception:
            update.message.reply_text('Wrong date format')
            return
        interval_start = context.args[0]
        interval_end = context.args[1]
        print_list(show_query(f"select * from actions where user_id = {update.message.chat_id} and start <= '{interval_end}' and end >= '{interval_start}'"), update, context)
    else:
        update.message.reply_text('Wrong count of parameters')


def main():
    # test2
    #   action
    #       id
    #       user_id
    #       text - event description
    #       start - start of event
    #       end - end of event
    with connect(host="localhost", user='root', password=root_password) as connection:
        with connection.cursor() as cursor:
            cursor.execute('create database if not exists test2')
            connection.commit()
    with connect(host="localhost", user='root', password=root_password, database='test2') as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
            create table if not exists actions(
                id INT NOT NULL,
                user_id INT NOT NULL,
                text VARCHAR(256),
                start DATE,
                end DATE,
                PRIMARY KEY (id)
            )
            """)
            connection.commit()


    updater = Updater(token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', get_info))
    dispatcher.add_handler(CommandHandler('help', get_info))
    dispatcher.add_handler(CommandHandler('add', add_task))
    dispatcher.add_handler(CommandHandler('delete', delete_task))
    dispatcher.add_handler(CommandHandler('watch', watch))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, get_info))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()