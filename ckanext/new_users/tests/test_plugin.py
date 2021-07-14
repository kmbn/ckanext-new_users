"""
Tests for plugin.py.

Tests are written using the pytest library (https://docs.pytest.org), and you
should read the testing guidelines in the CKAN docs:
https://docs.ckan.org/en/2.9/contributing/testing.html

To write tests for your extension you should install the pytest-ckan package:

    pip install pytest-ckan

This will allow you to use CKAN specific fixtures on your tests.

For instance, if your test involves database access you can use `clean_db` to
reset the database:

    import pytest

    from ckan.tests import factories

    @pytest.mark.usefixtures("clean_db")
    def test_some_action():

        dataset = factories.Dataset()

        # ...

For functional tests that involve requests to the application, you can use the
`app` fixture:

    from ckan.plugins import toolkit

    def test_some_endpoint(app):

        url = toolkit.url_for('myblueprint.some_endpoint')

        response = app.get(url)

        assert response.status_code == 200


To temporary patch the CKAN configuration for the duration of a test you can use:

    import pytest

    @pytest.mark.ckan_config("ckanext.myext.some_key", "some_value")
    def test_some_action():
        pass
"""
from bs4 import BeautifulSoup
import pytest

import ckan.plugins.toolkit as toolkit
from ckan.tests import factories

import ckanext.new_users.plugin as plugin


def user_env(user_dict):
    return {"REMOTE_USER": user_dict["name"]}


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SADeprecationWarning")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:alembic[.*]")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:babel[.*]")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:markdown[.*]")
@pytest.mark.ckan_config("ckan.plugins", "new_users")
@pytest.mark.usefixtures(
    "clean_db", "clean_index", "with_plugins", "with_request_context"
)
class TestNewUserPlugin:
    def test_anon_user_cannot_see_new_users(self, app):
        """An anon user shouldn't be able to access the new users view."""
        new_users_url = toolkit.url_for("new_users.new_users")
        new_users_response = app.get(new_users_url)

        assert "Need to be system administrator to administer" in new_users_response

    def test_new_users_view_normal_user(self, app):
        """A normal logged in user shouldn't be able to access the new users view."""
        user = factories.User()
        new_users_url = toolkit.url_for("new_users.new_users")
        new_users_response = app.get(new_users_url, extra_environ=user_env(user))

        assert "Need to be system administrator to administer" in new_users_response

    def test_new_users_view_sysadmin(self, app):
        """A sysadmin should be able to view the new users."""
        sysadmin = factories.Sysadmin()
        user = factories.User()
        new_users_url = toolkit.url_for("new_users.new_users")
        new_users_response = app.get(new_users_url, extra_environ=user_env(sysadmin))

        assert user["name"] in new_users_response

    def test_no_new_users_if_all_users_belong_to_an_org(self, app):
        """
        Getting the new users view when all users belong to
        organizations should list no users.
        """
        sysadmin = factories.Sysadmin()
        user_1 = factories.User()
        user_2 = factories.User()
        factories.Organization(name="test-org", users=[user_1, user_2])

        new_users_url = toolkit.url_for("new_users.new_users")
        new_users_response = app.get(new_users_url, extra_environ=user_env(sysadmin))

        new_users_response_html = BeautifulSoup(new_users_response.body)
        new_users_list = new_users_response_html.find_all(class_="srf-user")

        assert len(new_users_list) == 0

    def test_only_users_who_do_not_belong_to_an_org_are_listed(self, app):
        """
        The list of new users only includes users who do not belong to an
        organization and who are not sysadmins (who technically belong to all
        organizations).
        """
        sysadmin = factories.Sysadmin()
        user_1 = factories.User()
        user_2 = factories.User()
        factories.Organization(name="test-org", users=[user_1])

        new_users_url = toolkit.url_for("new_users.new_users")
        new_users_response = app.get(new_users_url, extra_environ=user_env(sysadmin))

        new_users_response_html = BeautifulSoup(new_users_response.body)
        new_users_list = new_users_response_html.find_all(class_="srf-user")
        new_user = new_users_list[0].find("a").text

        assert len(new_users_list) == 1
        assert user_2["display_name"] == new_user

    def test_no_new_users_menu_for_anon_user(self, app):
        """An anon user shouldn't see the new users menu item."""
        index_url = toolkit.url_for("home.index")
        index_response = app.get(index_url)
        index_response_html = BeautifulSoup(index_response.body)
        new_users_link = index_response_html.find(href="/ckan-admin/new-users")

        assert not new_users_link

    def test_no_new_users_menu_for_normal_user(self, app):
        """A normal logged in user shouldn't be able to see the new users menu item."""
        user = factories.User()
        index_url = toolkit.url_for("home.index")
        index_response = app.get(index_url, extra_environ=user_env(user))
        index_response_html = BeautifulSoup(index_response.body)
        new_users_link = index_response_html.find(href="/ckan-admin/new-users")

        assert not new_users_link

    def test_new_users_menu_for_sysadmin(self, app):
        """A sysadmin should be able to see the new users menu item."""
        sysadmin = factories.Sysadmin()
        index_url = toolkit.url_for("home.index")
        index_response = app.get(index_url, extra_environ=user_env(sysadmin))
        index_response_html = BeautifulSoup(index_response.body)
        new_users_link = index_response_html.find(href="/ckan-admin/new-users")

        assert new_users_link

    def test_new_users_count_is_0_if_all_users_belong_to_an_org(self, app):
        """
        The new users menu item badge should display 0 if all users belong to
        an organization.
        """
        sysadmin = factories.Sysadmin()
        user_1 = factories.User()
        user_2 = factories.User()
        factories.Organization(name="test-org", users=[user_1, user_2])
        index_url = toolkit.url_for("home.index")
        index_response = app.get(index_url, extra_environ=user_env(sysadmin))
        index_response_html = BeautifulSoup(index_response.body)
        new_users_link = index_response_html.find(href="/ckan-admin/new-users")
        new_users_badge = new_users_link.find(class_="badge")

        assert new_users_badge.text == "0"

    def test_new_users_count_equal_to_count_new_users(self, app):
        """
        The new users menu item badge should display the number of users who
        do not belong to an organization.
        """
        sysadmin = factories.Sysadmin()
        user_1 = factories.User()
        factories.User()
        factories.Organization(name="test-org", users=[user_1])
        index_url = toolkit.url_for("home.index")
        index_response = app.get(index_url, extra_environ=user_env(sysadmin))
        index_response_html = BeautifulSoup(index_response.body)
        new_users_link = index_response_html.find(href="/ckan-admin/new-users")
        new_users_badge = new_users_link.find(class_="badge")

        assert new_users_badge.text == "1"

    def test_all_organizations_are_included_in_select_menu(self, app):
        sysadmin = factories.Sysadmin()
        user = factories.User()
        org_1 = factories.Organization(name="org_1")
        org_2 = factories.Organization(name="org_2")
        new_users_url = toolkit.url_for("new_users.new_users")
        new_users_response = app.get(new_users_url, extra_environ=user_env(sysadmin))
        new_users_response_html = BeautifulSoup(new_users_response.body)
        select_menu = new_users_response_html.find(id="org-{}".format(user["name"]))
        options = [option.text for option in select_menu.find_all("option")]
        expected = [
            "Select an organization",
            org_1["display_name"],
            org_2["display_name"],
        ]

        assert options == expected

    def test_assign_user_to_org(self, app):
        sysadmin = factories.Sysadmin()
        user = factories.User()
        org_1 = factories.Organization(name="org_1")
        form = {"org": org_1["name"], "user": user["name"]}
        assign_user_url = toolkit.url_for("new_users.assign_user")
        assign_user_response = app.post(
            assign_user_url,
            data=form,
            extra_environ=user_env(sysadmin),
            follow_redirects=True,
        )
        assign_user_response_html = BeautifulSoup(assign_user_response.body)
        new_user_list = assign_user_response_html.find(id="new-user-list")
        new_users = new_user_list.find_all(class_="srf-user")

        assert len(new_users) == 0
