
# P4\_16 to Python converter

This program provides Python bindings for most of the functionalities and data structures of P4\_16.

The following installation steps work on Linux Mint 18.
You may have to adapt your approach for similar systems.


## Getting dependencies

~~~.bash
# get dependencies
sudo apt-get install libgc-dev libgmp-dev clang libclang-dev llvm-dev python-dev python-setuptools python-clang-3.8 libboost-dev libboost-python-dev

sudo pip install pyconfig

# get p4c
git clone https://github.com/p4lang/p4c
export P4C=`pwd`/p4c

# compile p4c
cd $P4C
make distclean
./bootstrap.sh 
CXXFLAGS="-fPIC -g" ./configure
make -j 4
~~~


## Compilation and usage

Use `make` to generate all necessary files.

If you get a compilation error about `libclang-3.8.so: cannot open shared object file`, an easy solution might be to do this before trying to run `make` again:

~~~.bash
sudo ln -s /usr/lib/x86_64-linux-gnu/libclang-3.8.so.1 /usr/lib/x86_64-linux-gnu/libclang-3.8.so
~~~

Afterwards, you can use the following command to demonstrate some of the available features.

~~~.bash
# test the P4C IR to Python bindings
python test_p4c.py "$P4C" $P4C/testdata/p4_16_samples/global-action.p4
~~~
