from flask import Blueprint
from flask.views import MethodView

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class NewUsersPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # IBlueprint
    def get_blueprint(self):
        """Return a Flask Blueprint object to be registered by the app."""
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = "templates"
        blueprint.add_url_rule(
            "/ckan-admin/new-users", view_func=NewUsersView.as_view("new_users")
        )
        blueprint.add_url_rule(
            "/ckan-admin/new-users/assign_user",
            view_func=AssignUserView.as_view("assign_user"),
        )

        return blueprint

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("fanstatic", "new_users")
        toolkit.add_ckan_admin_tab(
            config_,
            route_name="new_users.new_users",
            tab_label="New users",
            icon="user",
        )

    def get_helpers(self):
        return {
            "new_users_get_new_users": get_new_users,
            "new_users_get_new_users_count": get_new_users_count,
        }


def get_new_users(include_orgs=False):
    orgs = toolkit.get_action("organization_list")(
        {"ignore_auth": True}, {"all_fields": True, "include_users": True}
    )
    members = set()
    for org in orgs:
        for member in org["users"]:
            members.add(member["name"])
    all_users = toolkit.get_action("user_list")(
        {"ignore_auth": True}, {"all_fields": True}
    )
    non_sysadmin_users = [user["name"] for user in all_users if not user["sysadmin"]]
    new_users = list(set(non_sysadmin_users) - members)

    if include_orgs:
        return new_users, orgs
    else:
        return new_users


def get_new_users_count():
    return len(get_new_users())


class NewUsersView(MethodView):
    def get(self):
        try:
            context = {"user": toolkit.g.user, "auth_user_obj": toolkit.g.userobj}
            toolkit.check_access("sysadmin", context)
        except toolkit.NotAuthorized:
            toolkit.abort(
                403, toolkit._("Need to be system administrator to administer")
            )

        new_users, orgs = get_new_users(include_orgs=True)

        return toolkit.render(
            "new_users/admin/new_users.html",
            extra_vars={u"new_users": new_users, "orgs": orgs},
        )


class AssignUserView(MethodView):
    def post(self):
        context = {"user": toolkit.g.user}
        form = toolkit.request.form
        data_dict = {
            "id": form.get("org"),
            "username": form.get("user"),
            "role": "member",
        }

        try:
            toolkit.check_access("group_member_create", context, {"id": id})
        except toolkit.NotAuthorized:
            toolkit.abort(403, "Unauthorized to assign members to organizations")

        toolkit.get_action("group_member_create")(context, data_dict)

        return toolkit.h.redirect_to("new_users.new_users")
