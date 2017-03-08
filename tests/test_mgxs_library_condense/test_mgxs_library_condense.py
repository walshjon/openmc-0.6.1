#!/usr/bin/env python

import os
import sys
import glob
import hashlib
sys.path.insert(0, os.pardir)
from testing_harness import PyAPITestHarness
from input_set import PinCellInputSet
import openmc
import openmc.mgxs


class MGXSTestHarness(PyAPITestHarness):
    def _build_inputs(self):
        # Set the input set to use the pincell model
        self._input_set = PinCellInputSet()

        # Generate inputs using parent class routine
        super(MGXSTestHarness, self)._build_inputs()

        # Initialize a two-group structure
        energy_groups = openmc.mgxs.EnergyGroups(group_edges=[0, 0.625, 20.e6])

        # Initialize MGXS Library for a few cross section types
        self.mgxs_lib = openmc.mgxs.Library(self._input_set.geometry)
        self.mgxs_lib.by_nuclide = False

        # Test all MGXS types
        self.mgxs_lib.mgxs_types = openmc.mgxs.MGXS_TYPES + \
                                   openmc.mgxs.MDGXS_TYPES
        self.mgxs_lib.energy_groups = energy_groups
        self.mgxs_lib.num_delayed_groups = 6
        self.mgxs_lib.legendre_order = 3
        self.mgxs_lib.domain_type = 'material'
        self.mgxs_lib.build_library()

        # Initialize a tallies file
        self._input_set.tallies = openmc.Tallies()
        self.mgxs_lib.add_to_tallies_file(self._input_set.tallies, merge=False)
        self._input_set.tallies.export_to_xml()

    def _get_results(self, hash_output=False):
        """Digest info in the statepoint and return as a string."""

        # Read the statepoint file.
        statepoint = glob.glob(os.path.join(os.getcwd(), self._sp_name))[0]
        sp = openmc.StatePoint(statepoint)

        # Load the MGXS library from the statepoint
        self.mgxs_lib.load_from_statepoint(sp)

        # Build a condensed 1-group MGXS Library
        one_group = openmc.mgxs.EnergyGroups([0., 20.e6])
        condense_lib = self.mgxs_lib.get_condensed_library(one_group)

        # Build a string from Pandas Dataframe for each 1-group MGXS
        outstr = ''
        for domain in condense_lib.domains:
            for mgxs_type in condense_lib.mgxs_types:
                mgxs = condense_lib.get_mgxs(domain, mgxs_type)
                df = mgxs.get_pandas_dataframe()
                outstr += df.to_string() + '\n'

        # Hash the results if necessary
        if hash_output:
            sha512 = hashlib.sha512()
            sha512.update(outstr.encode('utf-8'))
            outstr = sha512.hexdigest()

        return outstr


if __name__ == '__main__':
    harness = MGXSTestHarness('statepoint.10.*', True)
    harness.main()