acousticbrainz-progtest
=======================

This project contains a programming test for the AcousticBrainz project.
Specifically, it is a subset of the AcousticBrainz server project,
which can be found at https://github.com/metabrainz/acousticbrainz-server
As this project is designed as a programming test, many parts of the database
and website have been removed from it.

Read on for instructions on how to install the server and for the
programming task.


## Installation

### Vagrant VM

The easiest way to start is to setup ready-to-use [Vagrant](https://www.vagrantup.com/)
VM. To do that [download](https://www.vagrantup.com/downloads.html) and install
Vagrant for your OS. Copy the config file

1. `config.py.sample` to `config.py`

After that you can spin up the VM and start working with it:

    $ vagrant up
    $ vagrant ssh

### Manually

Full installation instructions are available in the INSTALL.md file. This
process is *not* recommended for the programming test, but you can follow
it if you are comfortable with the technology stack.


### Login

To use the dataset tools you need to configure OAuth with MusicBrainz.
Log in to your MusicBrainz account (or create one if needed) and create
[a new application](https://musicbrainz.org/account/applications).

Choose a name (for example, "AcousticBrainz development"), set Type to "Web Application"
and set the Callback URL to http://localhost:8080/login/musicbrainz/post

Copy the OAuth Client ID and OAuth Client Secret values to
`config.py` as `MUSICBRAINZ_CLIENT_ID` and `MUSICBRAINZ_CLIENT_SECRET`.

You should now be able to use the menu in the top corner of your AcousticBrainz server
to log in.


## Running

You can start the web server after logging into the Vagrant virtual machine
with `vagrant ssh` (it will be available at http://localhost:8080/):

    $ cd acousticbrainz-server
    $ python manage.py runserver

# Programming test

We have started an API definition for a component of AcousticBrainz, called the dataset editor.
The task is to implement two methods API in this definition which modify the database.

In AcousticBrainz, a dataset has a name, and owner, and a list of _classes_.
Classes have a name, and a list of _members_, which are UUIDs.
These are represented by three tables in the database, `dataset`, `dataset_class`, and `dataset_class_member`.
Class names must be unique for a specific dataset, but could be the same on
different datasets.
A UUID can appear only once in a dataset class, but can appear in multiple
classes regardless of if they are in the same dataset or in different datasets.
You can see the definitions of these tables in the database setup scripts (`admin/sql/create_tables.sql`)


## Authentication and loading data

Once you start the webserver, navigate to http://localhost:8080 and log in using the link in the top right menu, creating
a MusicBrainz account if you need to. Once you have logged in, go to your user profile and generate an API key.

Using this API key you can create a test dataset using cURL. You can run this
from in the virtual machine or locally:

    $ curl -X POST -H "Authorization: Token <your api key>" -H "Content-Type: application/json" http://localhost:8080/api/v1/datasets/ -d @test-dataset.json

The request will return a UUID which is the ID of the dataset that has been created. You can access the contents of this dataset by going to the following URL in a browser
http://localhost:8080/api/v1/datasets/<dataset id>

Or by using curl:

    $ curl -H "Authorization: Token <your api key>"  http://localhost:8080/api/v1/datasets/86dd01cd-47c1-430a-8b24-efc1ecf6862a


## New endpoints

In the file `webserver/views/api/v1/datasets.py` there are four stubs for new API endpoints, which currently raise `NotImplementedError`

You have to implement the two methods `add_recordings` and `delete_recordings` based on the documentation which exists in the docstrings for these methods.
Use the _Example request_ blocks in the documentation to understand the format
that these enpoints accept.

Endpoints in the `webserver/views/api/v1/datasets.py` file should validate input and use helper methods in the `db/dataset.py` file.
You may need to write new methods here.

## Documentation

If you write new methods in order to make the implementation, ensure that you
write appropriate documentation for these methods.

## Testing

Make sure that you test the methods that you write, in `webserver/views/api/v1/test/test_datasets.py` and `db/test/test_dataset.py`
You can run tests by running the program `py.test` from the repository's main directory.

## Submission

You should fork the repository to your own github account and make a new branch.
When you have done this, open a pull request against this project.

## FAQ

<dl>
  <dt>Should I do any refactoring of methods to reduce code duplication?</dt>
  <dd>Consider the amount of time you want to spend on the task. We would prefer to see code duplication and a functional API endpoint, rather than a start at code deduplication without the endpoints working.</dd>
  <dt>Should I use SQL or an ORM?</dt>
  <dd>This specific project has been made using raw SQL queries. For consistency, continue to use these queries.</dd>
  <dt>Some API methods do a similar thing but don't use the same standards (different variable name syles, quoting styles, etc). What should I use?</dt>
  <dd>Because this is an old project written by many people it has some inconsistencies. Choose and duplicate one of the styles and don't worry about making other code consistent.</dd>
  <dt>What should I do if I find a behaviour that is undefined in the method API documentation?</dt>
  <dd>Choose a behaviour and add it to the documentation</dd>
  <dt>Do I also need to add tests?</dt>
  <dd>Yes, the task includes the development of tests for the required methods</dd>
</dl>
