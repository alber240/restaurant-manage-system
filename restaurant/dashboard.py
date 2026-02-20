from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard

class CustomDashboard(Dashboard):
    """
    Custom admin dashboard for Jet.
    Displays restaurant models and recent actions.
    """

    def init_with_context(self, context):
        # Model list for restaurant app
        self.children.append(modules.ModelList(
            title='Restaurant Management',
            models=('restaurant.*',)
        ))
        # Recent actions across all restaurant models
        self.children.append(modules.RecentActions(
            title='Recent Actions',
            limit=10,
            include_list=['restaurant.*']
        ))