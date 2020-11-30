#!/usr/bin/env python3
# Copyright 2020 jose
# See LICENSE file for licensing details.

import logging
import random
import string

from oci_image import OCIImageResource, OCIImageResourceError
from ops.charm import CharmBase
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    WaitingStatus,
)
from ops.framework import StoredState

logger = logging.getLogger(__name__)


class CharmCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        # initialize image resource
        self.image = OCIImageResource(self, 'mysql-image')
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.fortune_action, self._on_fortune_action)
        self._stored.set_default(things=[])


    def _on_config_changed(self, _):
        self._configure_pod()

    def _on_fortune_action(self, event):
        fail = event.params["fail"]

        if fail:
            event.fail(fail)
        else:
            event.set_results({"fortune": "A bug in the code is worth two in the documentation."})

    def _configure_pod(self):
        """Configure the K8s pod spec for Graylog."""
        if not self.unit.is_leader():
            self.unit.status = ActiveStatus()
            return

        spec = self._build_pod_spec()
        if not spec:
            return
        self.model.pod.set_spec(spec)
        self.unit.status = ActiveStatus()

    def _build_pod_spec(self):

        config = self.model.config

        # fetch OCI image resource
        try:
            image_info = self.image.fetch()
        except OCIImageResourceError:
            logging.exception('An error occurred while fetching the image info')
            self.unit.status = BlockedStatus('Error fetching image information')
            return {}

        # baseline pod spec
        spec = {
            'version': 3,
            'containers': [{
                'name': self.app.name,  # self.app.name is defined in metadata.yaml
                'imageDetails': image_info,
                'ports': [{
                    'containerPort': 3306,
                    'protocol': 'TCP'
                }],
                'envConfig': {
                    'MYSQL_ROOT_PASSWORD': 'Password',
                }
            }]
        }

        return spec

    def _password_secret(self, n=96):
        """The secret of size n used to encrypt/salt the MySQL root password

        Returns the already existing secret, if not exists generate one
        """
        if self._stored.password_secret:
            return self._stored.password_secret

        # TODO: is this how we want to generate random strings?
        # generate a random secret that will be used for the life of this charm
        chars = string.ascii_letters + string.digits
        secret = ''.join(random.choice(chars) for _ in range(n))
        self._stored.password_secret = secret

        return secret

if __name__ == "__main__":
    main(CharmCharm)
