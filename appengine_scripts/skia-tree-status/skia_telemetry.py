# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Skia Telemetry pages."""


import datetime
import json

from google.appengine.ext import db

from base_page import BasePage
import utils


FETCH_LIMIT = 50

TELEMETRY_ADMINS = (
    'rmistry@google.com',)


class TelemetryInfo(db.Model):
  """Contains a single row of Skia Telemetry data."""
  chrome_last_built = db.DateTimeProperty(required=True)
  gce_slaves = db.IntegerProperty(required=True)
  num_webpages = db.IntegerProperty(required=True)
  num_skp_files = db.IntegerProperty(required=True)
  last_updated = db.DateTimeProperty(required=True)
  skia_rev = db.IntegerProperty(required=True)
  chromium_rev = db.IntegerProperty(required=True)

  @classmethod
  def get_telemetry_info(cls):
    return cls.all().fetch(limit=1)[0]


class AdminTasks(db.Model):
  """Data model for Admin tasks."""
  username = db.StringProperty(required=True)
  task_name = db.StringProperty(required=True)
  requested_time = db.DateTimeProperty(required=True)
  completed_time = db.DateTimeProperty()

  @classmethod
  def get_all_admin_tasks(cls):
    return (cls.all()
               .order('-requested_time')
               .fetch(limit=FETCH_LIMIT))

  @classmethod
  def get_admin_task(cls, key):
    return db.GqlQuery(
        'SELECT * FROM AdminTasks WHERE __key__ = Key(\'AdminTasks\', %s);' % (
            key))

  @classmethod
  def get_all_pending_admin_tasks(cls):
    return (cls.all()
               .filter('completed_time =', None)
               .order('requested_time')
               .fetch(limit=FETCH_LIMIT))


class LuaTasks(db.Model):
  """Data model for Lua tasks."""
  username = db.StringProperty(required=True)
  lua_script = db.TextProperty(required=True)
  lua_script_link = db.LinkProperty()
  requested_time = db.DateTimeProperty(required=True)
  completed_time = db.DateTimeProperty()
  lua_output_link = db.LinkProperty()
  description = db.StringProperty()

  @classmethod
  def get_all_pending_lua_tasks(cls):
    return (cls.all()
               .filter('completed_time =', None)
               .order('requested_time')
               .fetch(limit=FETCH_LIMIT))

  @classmethod
  def get_all_lua_tasks(cls):
    return (cls.all()
               .order('-requested_time')
               .fetch(limit=FETCH_LIMIT))

  @classmethod
  def get_all_lua_tasks_of_user(cls, user):
    return (cls.all()
               .filter('username =', user)
               .order('-requested_time')
               .fetch(limit=FETCH_LIMIT))

  @classmethod
  def get_lua_task(cls, key):
    return db.GqlQuery(
        'SELECT * FROM LuaTasks WHERE __key__ = Key(\'LuaTasks\', %s);' %  key)


class TelemetryTasks(db.Model):
  """Data model for Telemetry tasks."""
  username = db.StringProperty(required=True)
  benchmark_name = db.StringProperty(required=True)
  benchmark_arguments = db.StringProperty()
  requested_time = db.DateTimeProperty(required=True)
  completed_time = db.DateTimeProperty()
  logs = db.BlobProperty()

  @classmethod
  def get_all_pending_telemetry_tasks(cls):
    return (cls.all()
               .filter('completed_time =', None)
               .order('requested_time')
               .fetch(limit=FETCH_LIMIT))

  @classmethod
  def get_all_telemetry_tasks_of_user(cls, user):
    return (cls.all()
               .filter('username =', user)
               .order('-requested_time')
               .fetch(limit=FETCH_LIMIT))


def add_telemetry_info_to_template(template_values, user_email):
  """Reads TelemetryInfo from the Datastore and adds it to the template."""
  telemetry_info = TelemetryInfo.get_telemetry_info()
  template_values['chrome_last_built'] = telemetry_info.chrome_last_built
  template_values['chromium_rev'] = telemetry_info.chromium_rev
  template_values['skia_rev'] = telemetry_info.skia_rev
  template_values['gce_slaves'] = telemetry_info.gce_slaves
  template_values['num_webpages'] = telemetry_info.num_webpages
  template_values['num_skp_files'] = telemetry_info.num_skp_files
  template_values['last_updated'] = telemetry_info.last_updated
  template_values['admin'] = user_email in TELEMETRY_ADMINS


class LuaScriptPage(BasePage):
  """Displays the lua script page."""

  @utils.require_user
  def get(self):
    return self._handle()

  @utils.require_user
  def post(self):
    requested_time = datetime.datetime.now()
    lua_script = db.Text(self.request.get('lua_script'))
    description = self.request.get('description')
    if not description:
      description = 'None'

    LuaTasks(
        username=self.user.email(),
        lua_script=lua_script,
        requested_time=requested_time,
        description=description).put()

    self.redirect('lua_script')

  def _handle(self):
    """Sets the information to be displayed on the main page."""
    template_values = self.InitializeTemplate(
        'Run Lua scripts on the SKP repository')

    add_telemetry_info_to_template(template_values, self.user.email())

    lua_tasks = LuaTasks.get_all_lua_tasks_of_user(self.user.email())
    template_values['lua_tasks'] = lua_tasks

    self.DisplayTemplate('lua_script.html', template_values)


class AllTasks(BasePage):
  """Displays all tasks (Admin, Lua, Telemetry)."""

  @utils.require_user
  def get(self):
    return self._handle()

  @utils.require_user
  def post(self):
    requested_time = datetime.datetime.now()
    admin_task = self.request.get('admin_task')

    AdminTasks(
        username=self.user.email(),
        task_name=admin_task,
        requested_time=requested_time).put()

    self.redirect('all_tasks')

  def _handle(self):
    """Sets the information to be displayed on the main page."""
    template_values = self.InitializeTemplate(
        'All Tasks')

    add_telemetry_info_to_template(template_values, self.user.email())

    admin_tasks = AdminTasks.get_all_admin_tasks()
    template_values['admin_tasks'] = admin_tasks
    lua_tasks = LuaTasks.get_all_lua_tasks()
    template_values['lua_tasks'] = lua_tasks

    self.DisplayTemplate('all_tasks.html', template_values)


class LandingPage(BasePage):
  """Displays the main landing page of Skia Telemetry."""

  @utils.require_user
  def get(self):
    return self._handle()

  def _handle(self):
    """Sets the information to be displayed on the main page."""

    template_values = self.InitializeTemplate('Skia Telemetry')

    add_telemetry_info_to_template(template_values, self.user.email())

    telemetry_tasks = TelemetryTasks.get_all_telemetry_tasks_of_user(
        self.user.email())
    template_values['telemetry_tasks'] = telemetry_tasks

    self.DisplayTemplate('skia_telemetry_landingpage.html', template_values)


class AddTelemetryTaskPage(BasePage):
  """Adds a telemetry task to the queue."""

  @utils.require_user
  def post(self):
    benchmark_name = self.request.get('benchmark_name')
    benchmark_arguments = self.request.get('benchmark_arguments')
    requested_time = datetime.datetime.now()

    TelemetryTasks(
        username=self.user.email(),
        benchmark_name=benchmark_name,
        benchmark_arguments=benchmark_arguments,
        requested_time=requested_time).put()

    self.response.out.write('<br/><br/>')
    self.response.out.write('Added the following to the queue-')
    self.response.out.write('<br/><br/>')
    self.response.out.write('username: %s<br/>' % self.user.email())
    self.response.out.write('benchmark_name: %s<br/>' % benchmark_name)
    self.response.out.write(
        'benchmark_arguments: %s<br/>' % benchmark_arguments)
    self.response.out.write('requested_time: %s' % requested_time)
    self.response.out.write('<br/><br/>')
    self.response.out.write(
        'You will receive an email when the benchmark run completes.')
    self.response.out.write('<br/><br/>')
    self.response.out.write('<a href=\'/skia-telemetry/\'>Back</a>')


class GetAdminTasksPage(BasePage):
  """Returns a JSON of all pending admin tasks in the queue."""

  def get(self):
    admin_tasks = AdminTasks.get_all_pending_admin_tasks()
    # Create a dict for JSON from the admin pending tasks.
    tasks_dict = {}
    count = 1
    for task in admin_tasks:
      task_dict = {}
      task_dict['key'] = task.key().id_or_name()
      task_dict['username'] = task.username
      task_dict['task_name'] = task.task_name
      tasks_dict[count] = task_dict
      count += 1
    self.response.out.write(json.dumps(tasks_dict, sort_keys=True))


class GetLuaTasksPage(BasePage):
  """Returns a JSON of all pending lua tasks in the queue."""

  def get(self):
    lua_tasks = LuaTasks.get_all_pending_lua_tasks()
    # Create a dict for JSON from the lua pending tasks.
    tasks_dict = {}
    count = 1
    for task in lua_tasks:
      task_dict = {}
      task_dict['key'] = task.key().id_or_name()
      task_dict['username'] = task.username
      task_dict['lua_script'] = task.lua_script
      tasks_dict[count] = task_dict
      count += 1
    self.response.out.write(json.dumps(tasks_dict, sort_keys=True))


class UpdateAdminTasksPage(BasePage):
  """Updates an admin task using its key."""

  def get(self):
    key = int(self.request.get('key'))
    completed_time = datetime.datetime.now()
    admin_task = AdminTasks.get_admin_task(key)[0]
    admin_task.completed_time = completed_time
    admin_task.put()

    self.response.out.write('<br/><br/>Added to the datastore-<br/><br/>')
    self.response.out.write('key: %s<br/>' % key)
    self.response.out.write('completed_time: %s<br/>' % completed_time)


class UpdateLuaTasksPage(BasePage):
  """Updates a lua task using its key."""

  def get(self):
    key = int(self.request.get('key'))
    lua_script_link = self.request.get('lua_script_link')
    lua_output_link = self.request.get('lua_output_link')
    completed_time = datetime.datetime.now()

    lua_task = LuaTasks.get_lua_task(key)[0]
    lua_task.lua_script_link = db.Link(lua_script_link)
    lua_task.lua_output_link = db.Link(lua_output_link)
    lua_task.completed_time = completed_time
    lua_task.put()

    self.response.out.write('<br/><br/>Added to the datastore-<br/><br/>')
    self.response.out.write('key: %s<br/>' % key)
    self.response.out.write('lua_script_link: %s<br/>' % lua_script_link)
    self.response.out.write('lua_output_link: %s<br/>' % lua_output_link)
    self.response.out.write('completed_time: %s<br/>' % completed_time)


class GetTelemetryTasksPage(BasePage):
  """Returns a JSON of all telemetry tasks in the queue."""

  def get(self):
    telemetry_tasks = TelemetryTasks.get_all_pending_telemetry_tasks()
    # Create a dict for JSON from the telemetry pending tasks.
    tasks_dict = {}
    count = 1
    for task in telemetry_tasks:
      task_dict = {}
      task_dict['key'] = task.key().id_or_name()
      task_dict['username'] = task.username
      task_dict['benchmark_name'] = task.benchmark_name
      task_dict['benchmark_arguments'] = task.benchmark_arguments
      tasks_dict[count] = task_dict
      count += 1
    self.response.out.write(json.dumps(tasks_dict, indent=4, sort_keys=True))


class UpdateInfoPage(BasePage):
  """Updates Telemetry info from the GCE master."""

  def get(self):
    chrome_last_built = datetime.datetime.fromtimestamp(
        float(self.request.get('chrome_last_built')))
    chromium_rev = int(self.request.get('chromium_rev'))
    skia_rev = int(self.request.get('skia_rev'))
    gce_slaves = int(self.request.get('gce_slaves'))
    num_webpages = int(self.request.get('num_webpages'))
    num_skp_files = int(self.request.get('num_skp_files'))
    last_updated = datetime.datetime.now()

    # Delete the old entry.
    TelemetryInfo.get_telemetry_info().delete()

    # Add the new updated one.
    TelemetryInfo(
        chrome_last_built=chrome_last_built,
        chromium_rev=chromium_rev,
        skia_rev=skia_rev,
        gce_slaves=gce_slaves,
        num_webpages=num_webpages,
        num_skp_files=num_skp_files,
        last_updated=last_updated).put()

    self.response.out.write('<br/><br/>Added to the datastore-<br/><br/>')
    self.response.out.write('chrome_last_built: %s<br/>' % chrome_last_built)
    self.response.out.write('chromium_rev: %s<br/>' % chromium_rev)
    self.response.out.write('skia_rev: %s<br/>' % skia_rev)
    self.response.out.write('gce_slaves: %s<br/>' % gce_slaves)
    self.response.out.write('num_webpages: %s<br/>' % num_webpages)
    self.response.out.write('num_skp_files: %s<br/>' % num_skp_files)
    self.response.out.write('last_updated: %s' % last_updated)
   

def bootstrap():
  # Guarantee that at least one instance of the required tables exist.
  if db.GqlQuery('SELECT __key__ FROM TelemetryInfo').get() is None:
    TelemetryInfo(
        chrome_last_built=datetime.datetime(1970, 1, 1),
        skia_rev=0,
        chromium_rev=0,
        gce_slaves=0,
        num_webpages=0,
        num_skp_files=0,
        last_updated=datetime.datetime.now()).put()
  
  if db.GqlQuery('SELECT __key__ FROM TelemetryTasks').get() is None:
    TelemetryTasks(
        username='Humpty Dumpty',
        benchmark_name='Sitting On A wall',
        benchmark_arguments='--try_not_to_fall',
        requested_time=datetime.datetime.now(),
        completed_time=datetime.datetime.now(),
        logs="I had a great fall").put()

  if db.GqlQuery('SELECT __key__ FROM LuaTasks').get() is None:
    LuaTasks(
        username='Initial Table Creation',
        lua_script='Test Lua Script',
        requested_time=datetime.datetime.now(),
        completed_time=datetime.datetime.now()).put()

  if db.GqlQuery('SELECT __key__ FROM AdminTasks').get() is None:
    AdminTasks(
        username='admin',
        task_name='Initial Table Creation',
        requested_time=datetime.datetime.now(),
        completed_time=datetime.datetime.now()).put()

