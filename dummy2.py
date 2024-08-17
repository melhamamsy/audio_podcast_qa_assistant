import os
from utils.utils import (create_or_update_dotenv_var,
                         initialize_env_variables,
                         )
from utils.grafana import (get_grafana_token_ids,
                           create_grafana_token,
                           delete_grafana_token,
                           get_grafana_data_source,
                           get_dashboard_uid_by_name,
                           drop_grafana_data_source
                           )




# Verify the change
print(f"MY_VARIABLE: {os.getenv('GRAFANA_ADMIN_TOKEN')}")


for token_id in get_grafana_token_ids():
    delete_grafana_token(token_id)
token = create_grafana_token()
if token:
    create_or_update_dotenv_var('GRAFANA_ADMIN_TOKEN', token)
    initialize_env_variables()