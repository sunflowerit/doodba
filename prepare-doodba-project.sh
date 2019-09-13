#!/usr/bin/env bash
chmod 750 $(pwd)
chmod 600 ./odoo-variables
mkdir -p ./auto/addons
chmod -R 750 ./auto
chmod 750 ./bin
sed -i 's|\/usr\/local\/bin|'$(pwd)'\/bin|g'  ./bin/autoupdate
chmod 740 ./bin/*
chmod 750 ./common
rm -fr ./common/build
ln ./bin/direxec ./common/build
chmod 750 ./common/build.d
chmod 740 ./common/build.d/*
mkdir -p ./common/conf.d
chmod 750 ./common/conf.d
rm -fr ./common/entrypoint
ln ./bin/direxec ./common/entrypoint
chmod 750 ./common/entrypoint.d
chmod 740 ./common/entrypoint.d/*
mkdir -p ./custom/src/private/
chmod -R 750 ./custom
chmod 750 ./lib
chmod 750 ./lib/doodbalib
chmod 740 ./lib/doodbalib/*
rm -fr $HOME/.local/lib/python2.7/site-packages/doodbalib
ln -s $(pwd)/lib/doodbalib $HOME/.local/lib/python2.7/site-packages/doodbalib
rm -fr $HOME/.local/lib/python2.7/site-packages/odoobaselib
ln -s $(pwd)/lib/doodbalib $HOME/.local/lib/python2.7/site-packages/odoobaselib
mkdir -p ./logfile
chmod 750 ./logfile
touch ./logfile/odoo.log
chmod 640 ./logfile/odoo.log
chmod 640 ./odoo-variables-example
chmod 740 ./prepare-doodba-project.sh
chmod 750 ./qa
mkdir -p ./qa/artifacts
chmod 750 ./qa/artifacts
chmod 740 ./qa/insider
chmod 640 ./requirements.txt
