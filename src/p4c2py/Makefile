
all:	check-env p4c.so

p4c.cpp.boosted:
	python generate_p4c_cpp.py ${P4C} p4c.cpp.boosted

p4c_common.so:
	clang++ -std=c++11 -shared -fPIC \
	    -I /usr/include/python2.7/ \
	    -lpython2.7 -lboost_python \
	    -lgc -lgmp -lgmpxx \
	    -I "${P4C}" \
	    ${P4C}/setup.cpp \
	    ${P4C}/ir/*.cpp \
	    ${P4C}/lib/*.cpp \
	    ${P4C}/frontends/p4-14/*.cpp \
	    ${P4C}/frontends/p4/*.cpp \
	    ${P4C}/frontends/p4/*/*.cpp \
	    ${P4C}/frontends/common/*.cpp \
	    ${P4C}/frontends/common/*/*.cpp \
	    ${P4C}/midend/*.cpp \
	    ${P4C}/backends/p4test/*.cpp \
	    -o p4c_common.so

p4c.so:	p4c_common.so p4c.cpp.boosted
	clang++ -std=c++11 -shared -fPIC \
	    -I "${P4C}" \
	    -I /usr/include/python2.7/ \
	    -lgc -lgmp -lgmpxx \
	    -Wl,-rpath=./ \
	    p4c_common.so \
	    p4c.cpp \
	    -o p4c.so

check-env:
ifndef P4C
    $(error P4C is undefined)
endif

clean:
	rm -f p4c.cpp.boosted p4c_common.so p4c.so
