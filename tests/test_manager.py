import pytest
from firebase_alchemy.mixin import FireMix
from firebase_alchemy.manager import Adaptor, ModelManager, SyncManager

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
    payload = {'msg': 'chat1 msg',
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
    # ---- MULTIPLE ADDS TEST ----
    payload = {'msg': 'chat2 msg',
               'who': aaron.name}
    chat2 = chat_manager.add(name='CHAT 2')
    chat_manager.push(chat2, payload)
    # verify data in chat2
    data = firebase_inspector.get(test_path, None)
    assert len(data.keys()) == 2
    # match the second key, since firebase write by timestamp
    level1_key = sorted(data.keys())[1]
    level2_key = data[level1_key].keys()[0]
    server_data = data[level1_key][level2_key]
    assert len(server_data.keys()) == 2
    assert server_data['msg'] == payload['msg']
    assert server_data['who'] == payload['who']
    # ---- MULTIPLE PUSH (TOPIC) TEST ----
    payload2 = {'msg': 'chat2 msg2',
                'who': aaron.name}
    chat_manager.push(chat2, payload2)
    # ensure the first msg in chat2 is preserved and unchanged
    data = firebase_inspector.get(test_path, None)
    assert len(data.keys()) == 2
    level1_key = sorted(data.keys())[1]
    level2_key = sorted(data[level1_key].keys())[0]
    chat2_msg1_data = data[level1_key][level2_key]
    assert len(chat2_msg1_data.keys()) == 2
    assert chat2_msg1_data['msg'] == payload['msg']
    assert chat2_msg1_data['who'] == payload['who']
    # verify msg2 in chat2 wrote correctly
    level2_key = sorted(data[level1_key].keys())[1]
    chat2_msg2_data = data[level1_key][level2_key]
    assert len(chat2_msg2_data.keys()) == 2
    assert chat2_msg2_data['msg'] == payload2['msg']
    assert chat2_msg2_data['who'] == payload2['who']
    # check msg2 in chat2
    # ---- DELETE TEST ----
    chat_manager.delete(chat1)
    assert len(firebase_inspector.get(test_path, None)) == 1
    chat_manager.delete(chat2)
    assert firebase_inspector.get(test_path, None) == None

def test_manager_firebase_branch_auto_adaption(user_model,
                                               chat_model,
                                               session,
                                               adaptor,
                                               firebase_inspector,
                                               fire_url):
    User = user_model
    Chat = chat_model
    test_path = 'chat' # should write into chat
    # users
    assert len(session.query(User).all()) == 0
    assert firebase_inspector.get(test_path, None) == None
    aaron = User(name='aaron')
    session.add(aaron)
    session.commit()
    assert session.query(User).first().name == 'aaron'
    # ---- CHAT MANAGER TEST ----
    chat_manager = ModelManager(adaptor,
                                Chat,
                                validator=['msg', 'who'])
    chat1 = chat_manager.add(name='Sunday Picnic')
    # verify wrote into targetted path
    assert len(firebase_inspector.get(test_path, None)) == 1
    payload = {'msg': 'test msg',
               'who': aaron.name}    
    chat_manager.push(chat1, payload)
    # verify wrote correct data wrote into two level down
    data = firebase_inspector.get(test_path, None)
    assert len(data.keys()) == 1
    level1_key = data.keys()[0]
    assert len(data[level1_key].keys()) == 1
    level2_key = data[level1_key].keys()[0]
    server_data = data[level1_key][level2_key]
    assert len(server_data.keys()) == len(payload.keys())
    payload_keys = payload.keys()
    for key in payload.keys():
        assert server_data[key] == payload[key]

def test_sync_manager_basic(dummy_model,
                            session,
                            adaptor,
                            firebase_inspector,
                            fire_url):
    Table = dummy_model
    test_path = 'test'
    assert len(session.query(Table).all()) == 0
    assert firebase_inspector.get(test_path, None) == None
    # -- Sync Manager test --
    sync_manager = SyncManager(adaptor, Table, firepath=test_path)
    payload = {
        'data1': 'qwert',
        'data2': 'asdfg'
    }
    # -- add function test --
    model_instance = sync_manager.add(sql_data='123456', payload=payload)
    data = firebase_inspector.get(test_path, None)
    assert len(data.keys()) == 1
    server_data = data[data.keys()[0]]
    assert len(payload.keys()) == len(server_data.keys())
    for key in payload.keys():
        assert payload[key] == server_data[key]
    # -- set function test, with entry param --
    payload['data1'] = '12345'
    sync_manager.set(model_instance, payload['data1'], entry='data1')
    data = firebase_inspector.get(test_path, None)
    assert len(data.keys()) == 1
    server_data = data[data.keys()[0]]
    assert len(payload.keys()) == len(server_data.keys())
    for key in payload.keys():
        assert payload[key] == server_data[key]
    # -- set function test, default params --
    new_payload = {
        'data3': '54321',
        'data4': '09876'
    }
    sync_manager.set(model_instance, payload)
    data = firebase_inspector.get(test_path, None)
    assert len(data.keys()) == 1
    server_data = data[data.keys()[0]]
    assert len(payload.keys()) == len(server_data.keys())
    for key in payload.keys():
        assert payload[key] == server_data[key]
