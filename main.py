import datetime
import os
import requests
import telebot
import mysql.connector
import matplotlib.pyplot as plt

token = "1676607568:AAGC7Y3PIOa1CDs0YMPsDXYXEl3a8YyVIJI"
bot = telebot.TeleBot(token)
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="010701",
    database='rates',
)
mycursor = mydb.cursor()


# mycursor.execute("CREATE TABLE rates (name VARCHAR(255), value VARCHAR(255), date TIMESTAMP)")
# mycursor.execute("DELETE FROM rates")
# mydb.commit()


@bot.message_handler(commands=['start'], content_types=['text'])
def send_welcome(message):
    bot.send_message(message.chat.id, """
This bot use USD as base currency and converts currency from the list.  
/list or /lst - returns list of all available rates.
/exchange - converts to the second currency with two decimal precision and return.
/history - return an image graph chart which shows the exchange rate graph/chart of the selected currency for the last 7 days.
""")


@bot.message_handler(commands=['list', 'lst'], content_types=['text'])
def handle_list(message):
    mycursor.execute("SELECT * FROM rates")
    myresult = mycursor.fetchall()
    now = datetime.datetime.now()
    if myresult and now - myresult[0][2] >= datetime.timedelta(minutes=10):
        resp = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
        data = resp.json()
        rates = data['rates']
        res = ''
        for rate in rates:
            if rate == 'USD':
                continue
            res += '{}: {}\n'.format(rate, "%.2f" % rates[rate])
            sql = "UPDATE rates SET name=(%s), value=(%s), date=(%s) WHERE name = (%s)"
            val = (rate, rates[rate], now, rate)
            mycursor.execute(sql, val)
    elif not myresult:
        resp = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
        data = resp.json()
        rates = data['rates']
        res = ''
        for rate in rates:
            if rate == 'USD':
                continue
            sql = "INSERT INTO rates (name, value , date) VALUES (%s, %s, %s)"
            val = (rate, rates[rate], now)
            mycursor.execute(sql, val)
    mydb.commit()
    mycursor.execute("SELECT * FROM rates")
    myresult = mycursor.fetchall()
    res = '\n'.join(['{}: {}'.format(i[0], "%.2f" % float(i[1])) for i in myresult])
    bot.send_message(message.chat.id, res)


@bot.message_handler(commands=['exchange'], content_types=['text'])
def handle_exchange(message):
    text = message.text.lower().split('to')
    if len(text) != 2:
        bot.send_message(message.chat.id, "Send correct message!")
        return
    else:
        first_part = text[0].split()
        resp = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
        data = resp.json()
        rates = data['rates']
        number = ''
        if '$' in text[0]:
            if first_part[1][1:].isnumeric():
                number = int(first_part[1][1:])
        elif 'usd' in text[0]:
            for word in first_part:
                if word.isnumeric():
                    number = int(word)
        else:
            bot.send_message(message.chat.id, "Write '$' before number or 'USD' after.")
            return
        if not number:
            bot.send_message(message.chat.id, "Send correct number!")
            return
        if ('usd' or '$' in text[0]) and number and text[1].upper().strip() in [i for i in rates]:
            second_currency = text[1].upper().strip()
            response = requests.get(
                'https://api.exchangeratesapi.io/latest?base=USD&symbols={}'.format(second_currency))
            currency = response.json()
            res = currency['rates'][second_currency]
            bot.send_message(message.chat.id,
                             "{} USD to {} is {}".format(number, second_currency, "%.2f" % float(res * number)))
        else:
            bot.send_message(message.chat.id, "Write correct second currency! The list of available auctions can be "
                                              "viewed by command /list")
            return


@bot.message_handler(commands=['history'], content_types=['text'])
def handle_history(message):
    response = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
    rates_list = response.json()
    new_rates = rates_list['rates']
    print(new_rates)
    try:
        name = message.text.split('/')[2][:4].strip()
    except IndexError:
        bot.send_message(message.chat.id, "Send correct message!")
        return
    if len(name) != 2:
        bot.send_message(message.chat.id, "Send correct message!")
    if name not in new_rates:
        bot.send_message(message.chat.id, "Write correct second currency! The list of available auctions can be "
                                          "viewed by command /list")
    now = datetime.datetime.now().date()
    d7 = now - datetime.timedelta(days=7)
    resp = requests.get('https://api.exchangeratesapi.io/history?start_at={}&end_at={}&base=USD'
                        '&symbols={}'.format(d7, now, name))
    data = resp.json()['rates']
    if not data:
        bot.send_message(message.chat.id, 'No exchange rate data is available for the selected currency for the last '
                                          '7 days.')
        return
    dict_rates = []
    dates = []
    rates = []
    for date in data:
        dates.append(date)
        dict_rates.append(data[date])
    for rate in dict_rates:
        rates.append(rate[name])

    # rates = data['rates']
    # line 1 points
    x1 = [date for date in dates]
    y1 = [rate for rate in rates]
    # plotting the line 1 points
    plt.plot(x1, y1, label="line 1")

    # naming the x axis
    plt.xlabel('x - date')
    # naming the y axis
    plt.ylabel('y - rate')
    # giving a title to my graph
    plt.title('The exchange rate graph of the {} for the last 7 days'.format(name))

    plt.savefig('graph.png')
    bot.send_photo(message.chat.id, photo=open('graph.png', 'rb'))
    os.remove('graph.png')
    plt.clf()


@bot.message_handler(commands=['examples'], content_types=['text'])
def handle_list(message):
    bot.send_message(message.chat.id, """
/list or /lst
/exchange $10 to CAD or /exchange 10 USD to CAD
/history USD/CAD for 7 days 
""")


bot.polling()
