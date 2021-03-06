import pytest
import sys, os
import time
import shlex
import shutil
import glob
import numpy as np
import subprocess as sp
import netCDF4 as nc

from helpers import setup_test_input_dir
from helpers import calc_regridding_err
from namcouple import namcouple as nam

def build_oasis(oasis_dir):

        oasis3mct_dir = os.path.join(oasis_dir, 'oasis3-mct')

        # First build oasis3-mct library.
        ret = sp.call(['make', '-C', oasis3mct_dir, 'ubuntu'])
        assert ret == 0

        # Build Fortran test code.
        ret = sp.call(['make', '-C', oasis_dir, 'clean'])
        assert ret == 0
        ret = sp.call(['make', '-C', oasis_dir])
        assert ret == 0


def run_oasis(oasis_dir, src_model, dest_model, src_npes=1, dest_npes=1):

        # Run model
        cur_dir = os.getcwd()
        os.chdir(oasis_dir)

        cmd = 'mpirun -np {} {} : -np {} {}'.format(src_npes, src_model,
                                                   dest_npes, dest_model)
        t0 = time.time()
        ret = sp.call(shlex.split(cmd))
        t1 = time.time()
        assert ret == 0

        os.chdir(cur_dir)

        return t1 - t0


def remap_to_mom(oasis_dir, input_dir, mom_hgrid, mom_mask):

        # Make oasis grids
        my_dir = os.path.dirname(os.path.realpath(__file__))
        cmd = [os.path.join(my_dir, '../', 'oasisgrids.py')]

        output_grids = os.path.join(oasis_dir, 'grids.nc')
        output_areas = os.path.join(oasis_dir, 'areas.nc')
        output_masks = os.path.join(oasis_dir, 'masks.nc')

        mom_args = ['--model_hgrid', mom_hgrid, '--model_mask', mom_mask,
                    '--grids', output_grids, '--areas', output_areas,
                    '--masks', output_masks, 'MOM']
        ret = sp.call(cmd + mom_args)
        assert ret == 0

        core2_hgrid = os.path.join(input_dir, 't_10.0001.nc')
        core2_args = ['--model_hgrid', core2_hgrid,
                      '--grids', output_grids, '--areas', output_areas,
                      '--masks', output_masks, 'CORE2']
        ret = sp.call(cmd + core2_args)
        assert ret == 0

        # Build models
        build_oasis(oasis_dir)

        runtime = run_oasis(oasis_dir, 'atm.exe', 'ice.exe')

        # Look at the output of the field.
        weights = os.path.join(oasis_dir,
                               'rmp_cort_to_momt_CONSERV_FRACNNEI.nc')

        with nc.Dataset(os.path.join(oasis_dir, 'src_field.nc')) as f:
            src = f.variables['Array'][:]
        with nc.Dataset(os.path.join(oasis_dir, 'dest_field.nc')) as f:
            dest = f.variables['Array'][:]

        return src, dest, weights, runtime


class TestOasis():
    """
    Run a basic OASIS example to test the generated config files.
    """

    @pytest.fixture
    def input_dir(self):
        return setup_test_input_dir()

    @pytest.fixture
    def oasis_dir(self):
        test_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(test_dir, 'oasis')

    @pytest.fixture
    def oasis3mct_dir(self):
        test_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(test_dir, 'oasis', 'oasis3-mct')

    def test_build(self, oasis_dir, oasis3mct_dir):
        """
        Build example Fortran code.
        """

        build_oasis(oasis_dir)

    @pytest.mark.conservation
    def test_remap_one_deg(self, input_dir, oasis_dir):
        """
        Use OASIS for a one degree remapping.
        """

        # Delete all netcdf files in oasis dir this will include the OASIS
        # configuration.
        for f in glob.glob(oasis_dir + '/*.nc'):
            try:
                os.remove(f)
            except FileNotFoundError as e:
                pass

        mom_hgrid = os.path.join(input_dir, 'grid_spec.nc')
        mom_mask = os.path.join(input_dir, 'grid_spec.nc')

        src, dest, weights, runtime = remap_to_mom(oasis_dir, input_dir,
                                                   mom_hgrid, mom_mask)
        rel_err = calc_regridding_err(weights, src, dest)

        print('OASIS relative error {}'.format(rel_err))
        print('OASIS time to make weights and remap one field {}'.format(runtime))

        assert rel_err < 1e-9

    @pytest.mark.conservation
    @pytest.mark.big_ram
    @pytest.mark.quarter_deg
    def test_remap_quarter_deg(self, input_dir, oasis_dir):
        """
        Use OASIS for a tenth degree remapping.
        """

        # Delete all netcdf files in oasis dir this will include the OASIS
        # configuration.
        for f in glob.glob(oasis_dir + '/*.nc'):
            try:
                os.remove(f)
            except FileNotFoundError as e:
                pass

        mom_hgrid = os.path.join(input_dir, 'ocean_hgrid.nc')
        mom_mask = os.path.join(input_dir, 'ocean_mask.nc')

        src, dest, weights, runtime = remap_to_mom(oasis_dir, input_dir,
                                                   mom_hgrid, mom_mask)
        rel_err = calc_regridding_err(weights, src, dest)

        print('OASIS relative error {}'.format(rel_err))
        print('OASIS time to make weights and remap one field {}'.format(runtime))

        assert rel_err < 1e-9

    @pytest.mark.conservation
    @pytest.mark.big_ram
    def test_remap_tenth_deg(self, input_dir, oasis_dir):
        """
        Use OASIS for a tenth degree remapping.
        """

        # Delete all netcdf files in oasis dir this will include the OASIS
        # configuration.
        for f in glob.glob(oasis_dir + '/*.nc'):
            try:
                os.remove(f)
            except FileNotFoundError as e:
                pass

        mom_hgrid = os.path.join(input_dir, 'ocean_01_hgrid.nc')
        mom_mask = os.path.join(input_dir, 'ocean_01_mask.nc')

        src, dest, weights, runtime = remap_to_mom(oasis_dir, input_dir,
                                                   mom_hgrid, mom_mask)
        rel_err = calc_regridding_err(weights, src, dest)

        print('OASIS relative error {}'.format(rel_err))
        print('OASIS time to make weights and remap one field {}'.format(runtime))

        assert rel_err < 1e-9

    @pytest.mark.esmf
    def test_remap_model_using_esmf(self, input_dir, oasis_dir):
        """
        Remap fields from atm -> land, atm -> ice and atm -> ocean. Each model
        has the following resolution:
        atm: 192x94
        land: 360x300
        ice: 1440x1080
        ocean: 3600x2700

        ESMF is used to create all the regridding weights files. Timing
        information is collected.
        """

        big_ram = False

        # Delete all netcdf files in oasis dir this will include the OASIS
        # configuration.
        for f in glob.glob(oasis_dir + '/*.nc'):
            try:
                os.remove(f)
            except FileNotFoundError as e:
                pass

        # Build models
        build_oasis(oasis_dir)

        my_dir = os.path.dirname(os.path.realpath(__file__))
        cmd = [os.path.join(my_dir, '../', 'remapweights.py')]

        atm_hgrid = os.path.join(input_dir, 't_10.0001.nc')

        land_hgrid = os.path.join(input_dir, 'grid_spec.nc')
        land_mask = os.path.join(input_dir, 'grid_spec.nc')

        ice_hgrid = os.path.join(input_dir, 'ocean_hgrid.nc')
        ice_mask = os.path.join(input_dir, 'ocean_mask.nc')

        ocean_hgrid = os.path.join(input_dir, 'ocean_01_hgrid.nc')
        ocean_mask = os.path.join(input_dir, 'ocean_01_mask.nc')

        atmt_to_lndt = os.path.join(oasis_dir,
                                    'rmp_atmt_to_lndt_CONSERVE.nc')
        atmt_to_icet = os.path.join(oasis_dir,
                                    'rmp_atmt_to_icet_CONSERVE.nc')
        icet_to_ocnt = os.path.join(oasis_dir,
                                    'rmp_icet_to_ocnt_CONSERVE.nc')

        # Build weights for atm -> land
        args = ['CORE2', 'MOM', '--src_grid', atm_hgrid,
                '--dest_grid', land_hgrid, '--dest_mask', land_mask,
                '--method', 'conserve', '--output', atmt_to_lndt,
                '--output_convention', 'SCRIP']
        ret = sp.call(cmd + args)
        assert ret == 0
        assert os.path.exists(atmt_to_lndt)
        print('Built atm -> land weights')

        # Build weights for atm -> ice
        args = ['CORE2', 'MOM', '--src_grid', atm_hgrid,
                '--dest_grid', ice_hgrid, '--dest_mask', ice_mask,
                '--method', 'conserve', '--output', atmt_to_icet,
                '--output_convention', 'SCRIP']
        ret = sp.call(cmd + args)
        assert ret == 0
        assert os.path.exists(atmt_to_icet)
        print('Built atm -> ice weights')

        # Build weights for ice -> ocean
        if big_ram:
            args = ['MOM', 'MOM', '--src_grid', ice_hgrid,
                    '--dest_grid', ocean_hgrid, '--dest_mask', ocean_mask,
                    '--method', 'conserve', '--output', icet_to_ocnt,
                    '--output_convention', 'SCRIP']
            ret = sp.call(cmd + args)
            assert ret == 0
            assert os.path.exists(icet_to_ocnt)
            print('Built ice -> ocean weights')

        # Setup namcouple for atm -> land and run
        config = nam.format(src_model='atmxxx', dest_model='landxx',
                            src_grid='atmt', dest_grid='lndt',
                            src_x = '192', src_y = '94',
                            dest_x = '360', dest_y = '300')
        with open(os.path.join(oasis_dir, 'namcouple'), 'w') as f:
            f.write(config)
        shutil.copy(os.path.join(oasis_dir, 'namcouple'),
                    os.path.join(oasis_dir, 'namcouple_atm_to_land'))

        runtime = run_oasis(oasis_dir, 'atm.exe', 'land.exe')
        print('Atm -> Land runtime {}'.format(runtime))

        # Setup namcouple for atm -> ice and run
        config = nam.format(src_model='atmxxx', dest_model='icexxx',
                            src_grid='atmt', dest_grid='icet',
                            src_x = '192', src_y = '94',
                            dest_x = '1440', dest_y = '1080')
        with open(os.path.join(oasis_dir, 'namcouple'), 'w') as f:
            f.write(config)
        shutil.copy(os.path.join(oasis_dir, 'namcouple'),
                    os.path.join(oasis_dir, 'namcouple_atm_to_ice'))

        runtime = run_oasis(oasis_dir, 'atm.exe', 'ice.exe')
        print('Atm -> Ice runtime {}'.format(runtime))

        # Setup namcouple for ice -> ocean and run
        if big_ram:
            confg = nam.format(src_model='icexxx', dest_model='oceanx',
                               src_grid='icet', dest_grid='ocnt',
                               src_x = '1440', src_y = '1080',
                                dest_x = '3600', dest_y = '2700')
            with open(os.path.join(oasis_dir, 'namcouple'), 'w') as f:
                f.write(config)
            shutil.copy(os.path.join(oasis_dir, 'namcouple'),
                        os.path.join(oasis_dir, 'namcouple_ice_to_ocean'))
            runtime = run_oasis(oasis_dir, 'ice.exe', 'ocean.exe')
            print('Ice -> Ocean runtime {}'.format(runtime))
