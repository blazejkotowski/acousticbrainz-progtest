from __future__ import absolute_import
from flask_login import login_user
from webserver.login import User
from webserver.testing import ServerTestCase
from db.testing import TEST_DATA_PATH
import db.exceptions
import webserver.views.api.exceptions
import webserver.views.api.v1.datasets
from utils import dataset_validator

import json
import mock
import os
import uuid


class APIDatasetViewsTestCase(ServerTestCase):

    def setUp(self):
        super(APIDatasetViewsTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = db.user.create(self.test_user_mb_name)
        self.test_user = db.user.get(self.test_user_id)
        self.correct_dataset = {
            "public": True,
            "name": "Dataset name",
            "description": "Dataset description",
            "author": self.test_user_id,
            "classes": [{"name": "abc", "description": "abc class", "recordings": []}]
        }



    def test_create_dataset_forbidden(self):
        """ Not logged in. """
        resp = self.client.post("/api/v1/datasets/")
        self.assertEqual(resp.status_code, 401)


    def test_create_dataset_no_data(self):
        """ No data or bad data POSTed. """
        self.temporary_login(self.test_user_id)

        resp = self.client.post("/api/v1/datasets/")
        self.assertEqual(resp.status_code, 400)
        expected = {"message": "Data must be submitted in JSON format."}
        self.assertEqual(resp.json, expected)

        resp = self.client.post("/api/v1/datasets/", data="test-not-json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json, expected)


    @mock.patch("db.dataset.create_from_dict")
    def test_create_dataset_validation_error(self, create_from_dict):
        """ return an error if create_from_dict returns a validation error """
        self.temporary_login(self.test_user_id)

        exception_error = "data is not valid"
        create_from_dict.side_effect = dataset_validator.ValidationException(exception_error)
        submit = json.dumps({"a": "thing"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        expected = {"message": exception_error}
        self.assertEqual(resp.json, expected)


    @mock.patch("db.dataset.create_from_dict")
    def test_create_dataset_fields_added(self, create_from_dict):
        """ Fields are added to the dict before validation if they don't exist. """
        self.temporary_login(self.test_user_id)

        exception_error = "data is not valid"
        create_from_dict.side_effect = dataset_validator.ValidationException(exception_error)
        submit = json.dumps({"a": "thing"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        # The `public` and `classes` fields are added
        create_from_dict.assert_called_once_with({"a": "thing", "public": True, "classes": []}, self.test_user["id"])


    @mock.patch("db.dataset.create_from_dict")
    def test_create_dataset(self, create_from_dict):
        """ Successfully creates dataset. """
        self.temporary_login(self.test_user_id)
        create_from_dict.return_value = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        # Json format doesn't matter as we mock the create response
        submit = json.dumps({"a": "thing"})
        resp = self.client.post("/api/v1/datasets/", data=submit, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        expected = {"success": True, "dataset_id": "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"}
        self.assertEqual(resp.json, expected)

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_not_exists(self, get):
        # Dataset doesn't exist
        get.side_effect = db.exceptions.NoDataFoundException()
        with self.assertRaises(webserver.views.api.exceptions.APINotFound):
            webserver.views.api.v1.datasets.get_check_dataset("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")
        get.assert_called_once_with("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_public(self, get):
        # You can access a public dataset
        dataset = {"test": "dataset", "public": True}
        get.return_value = dataset

        res = webserver.views.api.v1.datasets.get_check_dataset("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")
        self.assertEqual(res, dataset)
        get.assert_called_once_with("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_yours(self, get):
        # You can access your private dataset
        login_user(User.from_dbrow(self.test_user))
        dataset = {"test": "dataset", "public": False, "author": self.test_user_id}
        get.return_value = dataset

        res = webserver.views.api.v1.datasets.get_check_dataset("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")
        self.assertEqual(res, dataset)
        get.assert_called_once_with("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")

    @mock.patch("db.dataset.get")
    def test_get_check_dataset_private(self, get):
        # You can't access someone else's private dataset

        login_user(User.from_dbrow(self.test_user))
        # Dataset with a different author to the logged in user
        dataset = {"test": "dataset", "public": False, "author": (self.test_user_id+1)}
        get.return_value = dataset

        with self.assertRaises(webserver.views.api.exceptions.APINotFound):
            webserver.views.api.v1.datasets.get_check_dataset("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")
        get.assert_called_once_with("6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0")

    @mock.patch("db.dataset.get")
    def test_add_recordings_dataset_private(self, get):
        # Can't add recordings to dataset that doesn't belong to requesting user
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = {"public": True, "author": self.test_user_id+1, "classes": [{"name": "abc", "recordings": []}]}
        get.return_value = dataset
        response = self.client.put("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"class_name": "abc", "recordings": []}), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @mock.patch("db.dataset.get")
    def test_add_recordings_missing_field(self, get):
        # One of the required request fields is missing
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        get.return_value = self.correct_dataset.copy()
        response = self.client.put("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"recordings": []}), content_type="application/json")
        self.assertIn("You have to provide", response.data)
        self.assertEqual(response.status_code, 400)

    @mock.patch("db.dataset.get")
    def test_add_recordings_wrong_class(self, get):
        # Class you're trying to add recordings to the class that doesn't exist
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = {"public": True, "author": self.test_user_id, "classes": [{"name": "abc", "recordings": []}]}
        get.return_value = dataset
        response = self.client.put("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"class_name": "acdbc", "recordings": []}), content_type="application/json")
        print(response.data)
        self.assertIn("class doesn't exist", response.data)
        self.assertEqual(response.status_code, 400)

    @mock.patch("db.dataset.get")
    def test_add_recordings_data_not_json(self, get):
        # Request body is not JSON
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = {"public": True, "author": self.test_user_id, "classes": [{"name": "abc", "recordings": []}]}
        get.return_value = dataset
        response = self.client.put("/api/v1/datasets/%s/recordings" % dataset_id, content_type="application/text")
        self.assertIn("must be submitted in JSON format", response.data)
        self.assertEqual(response.status_code, 400)

    @mock.patch("db.dataset.get")
    @mock.patch("db.dataset.update")
    def test_add_recordings_correct(self, update, get):
        # Recording is correctly added to the dataset
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = self.correct_dataset.copy()
        get.return_value = dataset

        response = self.client.put("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"class_name": "abc", "recordings": ["e5323dc1-28ef-4cae-95fb-c3c9bb4391b0"]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(update.called)
        dataset_call = update.call_args[0][1]
        self.assertEqual(dataset_call["classes"][0]["recordings"], ["e5323dc1-28ef-4cae-95fb-c3c9bb4391b0"])

    @mock.patch("db.dataset.get")
    @mock.patch("db.dataset.update")
    def test_add_recordings_no_dup(self, update, get):
        # Recordings are not duplicated
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = self.correct_dataset.copy()
        dataset["classes"][0]["recordings"] = ["0a1db558-5b7c-49a2-a499-28eaf1896709"]
        get.return_value = dataset

        response = self.client.put("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"class_name": "abc", "recordings": ["0a1db558-5b7c-49a2-a499-28eaf1896709", "e5323dc1-28ef-4cae-95fb-c3c9bb4391b0"]}), content_type="application/json")
        dataset_call = update.call_args[0][1]
        self.assertEqual(sorted(dataset_call["classes"][0]["recordings"]), sorted(["0a1db558-5b7c-49a2-a499-28eaf1896709", "e5323dc1-28ef-4cae-95fb-c3c9bb4391b0"]))

    @mock.patch("db.dataset.get")
    def test_delete_recordings_dataset_private(self, get):
        # Can't add recordings to dataset that doesn't belong to requesting user
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = {"public": True, "author": self.test_user_id+1, "classes": [{"name": "abc", "recordings": []}]}
        get.return_value = dataset
        response = self.client.delete("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"class_name": "abc", "recordings": []}), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @mock.patch("db.dataset.get")
    def test_delete_recordings_missing_field(self, get):
        # One of the required request fields is missing
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        get.return_value = self.correct_dataset.copy()
        response = self.client.delete("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"recordings": []}), content_type="application/json")
        self.assertIn("You have to provide", response.data)
        self.assertEqual(response.status_code, 400)

    @mock.patch("db.dataset.get")
    def test_delete_recordings_wrong_class(self, get):
        # Class you're trying to add recordings to the class that doesn't exist
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = {"public": True, "author": self.test_user_id, "classes": [{"name": "abc", "recordings": []}]}
        get.return_value = dataset
        response = self.client.delete("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"class_name": "acdbc", "recordings": []}), content_type="application/json")
        print(response.data)
        self.assertIn("class doesn't exist", response.data)
        self.assertEqual(response.status_code, 400)

    @mock.patch("db.dataset.get")
    def test_delete_recordings_data_not_json(self, get):
        # Request body is not JSON
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = {"public": True, "author": self.test_user_id, "classes": [{"name": "abc", "recordings": []}]}
        get.return_value = dataset
        response = self.client.delete("/api/v1/datasets/%s/recordings" % dataset_id, content_type="application/text")
        self.assertIn("must be submitted in JSON format", response.data)
        self.assertEqual(response.status_code, 400)

    @mock.patch("db.dataset.get")
    @mock.patch("db.dataset.update")
    def test_delete_recordings_correct(self, update, get):
        # Recording is correctly removed from a dataset
        dataset_id = "6b6b9205-f9c8-4674-92f5-2ae17bcb3cb0"
        self.temporary_login(self.test_user_id)
        dataset = self.correct_dataset.copy()
        dataset = self.correct_dataset.copy()
        dataset["classes"][0]["recordings"] = ["0a1db558-5b7c-49a2-a499-28eaf1896709", "e5323dc1-28ef-4cae-95fb-c3c9bb4391b0"]
        get.return_value = dataset

        response = self.client.delete("/api/v1/datasets/%s/recordings" % dataset_id, data=json.dumps({"class_name": "abc", "recordings": ["0a1db558-5b7c-49a2-a499-28eaf1896709"]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(update.called)
        dataset_call = update.call_args[0][1]
        self.assertEqual(dataset_call["classes"][0]["recordings"], ["e5323dc1-28ef-4cae-95fb-c3c9bb4391b0"])
