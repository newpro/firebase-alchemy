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
        self.url = fire_url
        self.maps = {} # key: table name, value: firepath

    def _map(self, table_name, firepath):
        self.maps[table_name] = firepath

    def _write(self, fireid, model_cls, **model_args):
        """add a db entry, and return the new model instance
        """
        #TODO: name is not safe??? need decoupling
        new_model = model_cls(fireid=fireid, **model_args)
        self.session.add(new_model)
        self.session.commit()
        return new_model

def _append_paths(base, extra):
    """Give a base path and a string, expand the path.
    """
    if base[-1:] == '/':
        base = base[:-1]
    if extra[0] == '/':
        extra = extra[1:]
    if extra[-1:] == '/':
        extra = extra[:-1]
    return base + '/' + extra

class AbstractManager(object):
    """General manager
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
                    self.firepath = _append_paths(self.firepath, path)
            else:
                self.firepath = firepath
        else: # no firepath
            # user default from mixin
            if not model_cls.__firepath__:
                raise Exception('No firepath available')
            self.firepath = model_cls.__firepath__
        # record mapping
        self.adaptor._map(self.model_cls.__name__.lower(),
                          self.firepath)

    def _path(self, model_instance, full=False):
        """give a model instance, retrive the firepath of it
        """
        firepath = self.firepath
        if full:
            firepath  = _append_paths(self.adaptor.url, firepath)
        return _append_paths(firepath, model_instance.fireid)

    def _validate(self, payload, key=None):
        """helper function, gives a payload and validate the format

        either raise an exception or do nothing.

        Optional: key, only validate if the payload
        can fill into key value pair
        """
        if not self.validator:
            return # no validation required
        if not key:
            # validates the whole payload
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
        else:
            # only validate for key pair
            if isinstance(self.validator, dict):
                if key in self.validator and (not isinstance(payload, self.validator[key])):
                    raise Exception('Wrong value format for key. K: {}, format: {}'.format(payload,
                                                                                           self.validator[key]))

    def _build(self, init_payload=True, **model_args):
        """build a instance: create a spaceholder in firebase, write
        into db, and return the new created model instance

        Optional: init_payload, inject initial data into space holder
        """
        fireid = self.adaptor.fire.post(url=self.firepath,
                                         data=init_payload)['name']
        return self.adaptor._write(fireid=fireid,
                                   model_cls=self.model_cls,
                                   **model_args)

    # -- Available operations for all managers --
    def delete(self, model_instance):
        """propagate delete in firebase first, then delete a model instance.
        """
        self.adaptor.fire.delete(self.firepath, model_instance.fireid)
        self.adaptor.session.delete(model_instance)
        self.adaptor.session.commit()

    def get(self, model_instance, subpath=None):
        """get data for a model instance. 
        """
        return self.adaptor.fire.get(self._path(model_instance),
                                     subpath)

class SyncManager(AbstractManager):
    """Sync manager use to build and maintain one to one relationship
    between one sql-alchemy row and one firebase document.

    for example: one person in db response to a firebase document about its state.
    """
    def __init__(self, *args, **kwargs):
        super(ModelManager, self).__init__(*args, **kwargs)

    def add(self, payload, **model_args):
        """add a db entry and a payload as its firebase state, commit changes
        """
        return self._build(init_payload=payload, **model_args)

    def set(self, model_instance, data, entry=None):
        """Completely overwrite the existing firebase entry for the model_instance
        """
        # extract fire id and set data
        if entry:
            self._validate(payload=data, key=entry)
            self.adaptor.fire.put(url=self._path(model_instance),
                                  name=entry,
                                  payload=data)
        else:
            self._validate(payload=data)
            self.adaptor.fire.put(url=self.firepath,
                                  name=model_instance.fireid,
                                  payload=data)

class ModelManager(AbstractManager):
    """ModelManager use to build and maintain one to multiple relationship
    between one sql-alchemy row to firebase documents.

    For example: one chat responses multiple firebase document.

    DB operations sheilding
    """
    def __init__(self, *args, **kwargs):
        super(ModelManager, self).__init__(*args, **kwargs)

    def add(self, **model_args):
        """add a new instance in sql session and firebase, commit change

        Return: new sqlalchemy model instance.
        """
        # record in firebase, fetch id
        return self._build(**model_args)

    def push(self, model_instance, payload):
        """push a piece of info in firebase based on model instance.
        """
        # validate the payload
        self._validate(payload)
        self.adaptor.fire.post(self._path(model_instance),
                               payload)

    def get_path(self, model_instance, full=True):
        """return the path to firebase instance, normally used for client to listen to.
        """
        return self._path(model_instance, full=full)
