import logging
import pytest
import waiting
import os
import random
from contextlib import suppress
from string import ascii_lowercase
from typing import Optional
from tests.base_test import BaseTest
from tests.conftest import env_variables
from assisted_service_client.rest import ApiException
from test_infra import assisted_service_api, consts, utils

def random_name():
    return ''.join(random.choice(ascii_lowercase) for i in range(10))


@pytest.fixture()
def api_client():
    def get_api_client(offline_token=env_variables['offline_token'], **kwargs):
        url = env_variables['remote_service_url']

        if not url:
            url = utils.get_local_assisted_service_url(
                utils.get_env('PROFILE'), utils.get_env('NAMESPACE'), 'assisted-service', utils.get_env('DEPLOY_TARGET'))
        
        return assisted_service_api.create_client(url, offline_token, **kwargs)


    yield get_api_client

class TestAuth(BaseTest):
    @pytest.fixture()
    def cluster(self):
        clusters = []
        api_clients = []
        def get_cluster_func(api_client, cluster_name: Optional[str] = None):
            api_clients.append(api_client)
            if not cluster_name:
                cluster_name = random_name()

            res = api_client.create_cluster(cluster_name,
                                            ssh_public_key=env_variables['ssh_public_key'],
                                            openshift_version=env_variables['openshift_version'],
                                            pull_secret=env_variables['pull_secret'],
                                            base_dns_domain=env_variables['base_domain'],
                                            vip_dhcp_allocation=env_variables['vip_dhcp_allocation'])
            clusters.append(res)
            return res

        yield get_cluster_func
        for client in api_clients:
            for cluster in clusters:
                with suppress(ApiException):
                    client.delete_cluster(cluster.id)

    def _send_dummy_step_result(self, api_client, cluster_id, host_id):
        api_client.host_post_step_result(
            cluster_id, 
            host_id,
            step_type="inventory",
            step_id="inventory-e048e0db",
            exit_code=0,
            output="null"
        )

    @pytest.mark.regression
    def test_user_authorization_negative(self, api_client, node_controller, cluster):
        client_user1 = api_client()
        client_user2 = api_client(offline_token=env_variables['second_offline_token'])

        user1_cluster_id = cluster(client_user1, env_variables['cluster_name']).id

        #user2 cannot get user1's cluster 
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.get_cluster,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        #user2 cannot delete user1's cluster
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.delete_cluster,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        #user2 cannot generate ISO user1's cluster
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.generate_and_download_image,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        self.generate_and_download_image(cluster_id=user1_cluster_id, api_client=client_user1)
        # Boot nodes into ISO
        node_controller.start_all_nodes()
        # Wait until hosts are discovered and update host roles
        self.wait_until_hosts_are_discovered(cluster_id=user1_cluster_id, api_client=client_user1)
        self.set_host_roles(cluster_id=user1_cluster_id, api_client=client_user1)
        self.set_network_params(
            cluster_id=user1_cluster_id,
            api_client=client_user1,
            controller=node_controller
        )
        
        #user2 cannot patch user1's cluster
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.set_network_params,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id,
            controller=node_controller
        )

        #user2 cannot list user2's hosts
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.get_cluster_hosts,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        #user2 cannot trigger user2's cluster install
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.start_cluster_install,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        #start cluster install
        self.start_cluster_install(user1_cluster_id, client_user1)
        
        #user2 cannot download files from user2's cluster
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.download_kubeconfig_no_ingress,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        #user2 cannot get user2's cluster install config
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.get_cluster_install_config,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        #user2 cannot cancel user2's cluster install
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.cancel_cluster_install,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        self.wait_for_nodes_to_install(cluster_id=user1_cluster_id, api_client=client_user1)
        self.wait_for_cluster_to_install(cluster_id=user1_cluster_id, api_client=client_user1)

        #user2 cannot get user2's cluster credentials
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.get_cluster_admin_credentials,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )


    @pytest.mark.regression
    def test_agent_authorization_negative(self, api_client, node_controller, cluster):
        client_user1 = api_client()
        client_user2 = api_client(
            offline_token='', 
            pull_secret=env_variables['second_pull_secret'],
            wait_for_api=False
        )
        
        user1_cluster_id = cluster(client_user1, env_variables['cluster_name']).id

        #agent with user2 pull secret cannot get user1's cluster details
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.get_cluster,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        #agent with user2 pull secret cannot register to user1's cluster
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.register_dummy_host,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        self.generate_and_download_image(cluster_id=user1_cluster_id, api_client=client_user1)
        # Boot nodes into ISO
        node_controller.start_all_nodes()
        # Wait until hosts are discovered and update host roles
        self.wait_until_hosts_are_discovered(cluster_id=user1_cluster_id, api_client=client_user1)
        self.set_host_roles(cluster_id=user1_cluster_id, api_client=client_user1)
        self.set_network_params(cluster_id=user1_cluster_id,
                                api_client=client_user1,
                                controller=node_controller
                                )
        #agent with user2 pull secret cannot list cluster hosts
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.get_cluster_hosts,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        host_ids = self.get_cluster_host_ids(user1_cluster_id, client_user1)

        #agent with user2 pull secret cannot get next step
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.host_get_next_step,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id,
            host_id=host_ids[0]
        )

        #agent with user2 pull secret cannot update on next step
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self._send_dummy_step_result,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id,
            host_id=host_ids[0]
        )

        self.start_cluster_install(cluster_id=user1_cluster_id, api_client=client_user1)

        #agent with user2 pull secret cannot update install progress
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.host_fail_cluster_install,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id,
            host_id=host_ids[0]
        )

        #agent with user2 pull secret cannot download files
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.download_kubeconfig_no_ingress,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )

        self.wait_for_nodes_to_install(user1_cluster_id, client_user1)

        #agent with user2 pull secret cannot complete installation
        self.assert_http_error_code(
            api_client=client_user2,
            api_call=self.complete_cluster_installation,
            status=404,
            reason="Not Found",
            cluster_id=user1_cluster_id
        )








        


        


        