from firebase.firebase import FirebaseApplication

__all__ = [
    'Adaptor',
    'ModelManager'
]

class Adaptor(object):
    """Manager for one db instance
    """
    def __init__(self, session, fire_url):
        """Init adaptor

        Args:
            session(sqlalchemy session): db operation session
            fire(firebase class): fire operation reference
        """
        self.session = session
        self.fire = FirebaseApplication(fire_url)
        self.maps = {} # key: table name, value: firepath

    def _map(self, table_name, firepath):
        self.maps[table_name] = firepath

def _getpath(fire_path, fire_id):
    """Give a path and id, merge them together.
    """
    if fire_path[-1:] == '/':
        return path + fire_id
    else:
        return path + '/' + fire_id

class ModelManager(object):
    """DB operations sheilding
    """
    def __init__(self, adaptor, model_cls, firepath=None, validator=None):
        """Init

        Args:
            model(a sqlalchemy model with mixin): model class
            firepath(a string or list): the location should be insert for firebase
        """
        self.adaptor = adaptor
        self.model_cls = model_cls
        self.validator = validator
        if validator:
            if (not isinstance(validator, dict)) and (not isinstance(validator, list)):
                raise Exception('validator has to be dict or list')
        if firepath:
            if isinstance(firepath, list): # allow list
                # put in a string
                self.firepath = ''
                for path in firepath:
                    self.firepath += path
            else:
                self.firepath = firepath
        else: # no firepath
            # user default from mixin
            self.firepath = model_cls.__firepath__
        # record mapping
        self.adaptor._map(self.model_cls.__name__.lower(),
                          self.firepath)

    def add(self, **args):
        """add a new instance in sql session and firebase, commit change

        Return: new model instance.
        """
        # record in firebase, fetch id
        #TODO: name is not safe, need decoupling
        fireid = self.adaptor.fire.post(self.firepath, True)['name']
        new_model = self.model_cls(fireid=fireid, **args)
        self.adaptor.session.add(new_model)
        self.adaptor.session.commit()
        return new_model

    def push(self, model_instance, payload):
        """push a piece of info in firebase based on model instance.
        """
        # validate the payload
        if self.validator:
            try:
                if isinstance(self.validator, list): # a list of keys
                    for key in self.validator:
                        if not (key in payload):
                            raise Exception()
                else: # dict. key: payload keys, value: type
                    # Check instance type matchs
                    for key in self.validator:
                        if (not (key in payload)) or (not isinstance(payload[key], self.validator[key])):
                            raise Exception()
            except:
                raise Exception('Wrong payload format: p:{}, v:{}'.format(payload, self.validator))
        # calcuate path
        path = _getpath(self.firepath, model_instance.fireid)
        self.adaptor.fire.post(path, payload)

    def delete(self, model_instance):
        """propagate delete in firebase first, then delete a model instance.
        """
        self.adaptor.fire.delete(self.firepath, model_instance.fireid)
        self.adaptor.session.delete(model_instance)
        self.adaptor.session.commit()

    def fire_path(self, model_instance):
        return _getpath(self.firepath, model_instance.fireid)
