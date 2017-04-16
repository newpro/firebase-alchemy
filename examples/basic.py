from example import *

# !!! Link managers !!!
adaptor = Adaptor(session, FIRE_URL)
# for each model class that link to firebase, bind a manager
chat_manager = ModelManager(adaptor, Chat, firepath='chats', validator=['msg', 'who'])

# users
aaron = User(name='aaron')
bill = User(name='bill')
colin = User(name='colin')
session.add_all([aaron, bill, colin])
session.commit()

# chats
chat1 = chat_manager.add(name='Sunday Picnic')
chat2 = chat_manager.add(name='Colin surprise birthday party')

# some relationships
chat1.users.append(aaron)
chat1.users.append(colin)
chat2.users.append(aaron)
chat2.users.append(bill)
session.commit()

# fetch queue as fast and easy as sqlalchemy!
print '{} in chat for {}: {} '.format(colin.name, chat1.name, colin in chat1.users)
print '{} in chat for {}: {} '.format(colin.name, chat2.name, colin in chat2.users)

# chat about something
chat_manager.push(chat2, {'msg': 'Let us throw colin a suprise party!',
                          'who': aaron.name})
chat_manager.push(chat2, {'msg': 'Yeah agree!',
                          'who': bill.name})

# delete the instance in db and firebase
#chat_manager.delete(chat2) # uncomment this to remove chat
