import pytest
from firebase_alchemy.mixin import FireMix
from firebase_alchemy.manager import Adaptor, ModelManager

def test_chat_manager_basic(user_model,
                            chat_model,
                            session,
                            adaptor,
                            firebase_inspector,
                            fire_url):
    User = user_model
    Chat = chat_model
    test_path = 'test'
    # users
    assert len(session.query(User).all()) == 0
    assert firebase_inspector.get(test_path, None) == None
    aaron = User(name='aaron')
    session.add(aaron)
    session.commit()
    assert len(session.query(User).all()) == 1
    # ---- CHAT MANAGER TEST ----
    chat_manager = ModelManager(adaptor,
                                Chat,
                                firepath=test_path,
                                validator=['msg', 'who'])
    chat1 = chat_manager.add(name='Sunday Picnic')
    assert len(firebase_inspector.get(test_path, None)) == 1
    chat1.users.append(aaron)
    session.commit()
    assert aaron in chat1.users
    payload = {'msg': 'test msg',
               'who': aaron.name}
    chat_manager.push(chat1, payload)
    # -- inspect data just wrote in from server side --
    data = firebase_inspector.get(test_path, None)
    level1_key = data.keys()[0]
    level2_key = data[level1_key].keys()[0]
    server_data = data[level1_key][level2_key]
    # -- verify exact data on server side --
    assert len(server_data.keys()) == 2
    assert server_data['msg'] == payload['msg']
    assert server_data['who'] == payload['who']
    # ---- GET TEST ----
    get_data = chat_manager.get(chat1)
    msg_data = get_data[get_data.keys()[0]]
    assert len(msg_data.keys()) == 2
    assert msg_data['msg'] == payload['msg']
    assert msg_data['who'] == payload['who']
    # ---- GET PATH TEST ----
    path = chat_manager.get_path(chat1)
    assert path == fire_url + test_path + '/' + level1_key
    path = chat_manager.get_path(chat1, full=False)
    assert path == test_path + '/' + level1_key
    # ---- DELETE TEST ----
    chat_manager.delete(chat1)
    assert firebase_inspector.get(test_path, None) == None
