import os
import sys

from curses import wrapper

from api  import API, APIError, APIConnectionError, APIInvalidDataError
from env  import Env
from cli  import CLI
from log  import Logger
from user import User

class CaText():
    def __init__(self):

        # need a consistent reference to the root of this directory
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__),'..'))

        # root environment variable manager
        self.env = Env(self.get_path('env.ct'))
        self.env.set('CURRENT_USER','')

        # root logger
        self.logger = Logger('MAIN', self.project_root, self.env)

        # set up our "GUI" which is really just a curses CLI
        self.cli = CLI(self.logger, self.env, self.get_path)

        # set up the interface w/ our REST API
        try:
            self.api = API(self.logger, self.env)
        except APIError as e:
            self.logger.critical(e)
            self.cli.status('ERROR: {}'.format(e))
            self.cli.wait()
            sys.exit(-1)

        # make sure we have a path to hold our user data
        self.users_path = self.get_path('.users')
        if not(os.path.exists(self.users_path)):
            self.logger.debug('creating ".users" directory')
            os.mkdir(self.users_path)

        # try to get a user
        self.current_user = self.select_user()
        self.cli.status('Successfully logged in as {}'.format(self.current_user.name))
        self.env.set('CURRENT_USER', self.current_user.name)
        self.logger.info('current user: {}'.format(self.current_user.name))

        # go to the lobby
        self.enter_lobby()

    def enter_lobby(self):
        self.logger.info('entering lobby')
        data = self.api.get_lobby(self.current_user.token)
        self.cli.change_mode('lobby', data)

        self.cli.wait()

    def select_user(self):
        '''
        generates a list of available users to select from, or enables
        the user to login thru the web endpoint

        @return User() corresponding to the choice
        '''

        default_user = self.env.get('DEFAULT_USER')
        self.logger.debug('default user: {}'.format(default_user))
        user = self.get_user(default_user)

        while user is None:

            username = self.cli.input(' - username: ')
            user = self.get_user(username)

            if user is None and len(username):
                password = self.cli.input(' - password: ', visible=False)
                self.logger.debug('username:{}, password:{}'.format(username,'*'*len(password)))
                self.cli.status('Querying CatOnline database ... ')
                user = self.save_user(username, password)

        return user

    def get_path(self, *paths):
        ''' get path under project root '''
        return os.path.join(self.project_root, *paths)

    def get_user(self, name):
        if name == None:
            return None
        return User(self.project_root, self.logger).read(name)

    def save_user(self, username, password):
        try:
            user_data, token = self.authenticate(username, password)
            return User(self.project_root, self.logger).set(user_data, token)
        except APIError as e:
            self.logger.error(e)
            if isinstance(e, APIInvalidDataError):
                self.cli.status(str(e))
            elif isinstance(e, APIConnectionError):
                self.cli.status('ERROR: only local logins are available')
                self.cli.wait()


    def authenticate(self, username, password):
        ''' either use an authentication token or get a new one '''
        return self.api.post_login(username, password)


class CaTextError(Exception):
    pass


def main(*args, **kwargs):
    app = CaText()
    app.cli.quit()


if __name__ == '__main__':
    wrapper(main)
