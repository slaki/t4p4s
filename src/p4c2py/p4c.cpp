#include <boost/python.hpp>
#include <boost/noncopyable.hpp>
#include <boost/preprocessor/stringize.hpp>

#include <list>

#include "ir/ir.h"
#include "ir/vector.h"
#include "lib/log.h"
#include "lib/error.h"
#include "lib/exceptions.h"
#include "lib/gc.h"
#include "lib/crash.h"
#include "lib/nullstream.h"
#include "frontends/common/options.h"
#include "frontends/common/parseInput.h"
#include "frontends/p4/evaluator/evaluator.h"
#include "frontends/p4/frontend.h"
#include "frontends/p4/toP4/toP4.h"
#include "backends/p4test/midend.h"

const IR::P4Program* load_p4_main(int argc, char *const argv[], bool run_midend) {
    // setup_gc_logging();
    setup_signals();

    CompilerOptions options;
    options.langVersion = CompilerOptions::FrontendVersion::P4_16;

    if (options.process(argc, argv) != nullptr)
        options.setInputFile();
    if (::errorCount() > 0) {
        return nullptr;
    }

    auto program = parseP4File(options);

    if (program != nullptr && ::errorCount() == 0) {
        P4::FrontEnd fe;
        program = fe.run(options, program);
        if (run_midend && program != nullptr && ::errorCount() == 0) {
            P4Test::MidEnd midEnd(options);
            (void)midEnd.process(program);
        }
        return program;
    }
    return nullptr;
}

const IR::P4Program* load_p4(const std::list<std::string>& l, bool run_midend) {
  const char ** array_orig = new const char*[l.size()];
  unsigned index = 0;
  for (std::list<std::string>::const_iterator it = l.begin(); it != l.end(); ++it) {
    array_orig[index]= it->c_str();
    index++;
  }

  char *const * array = const_cast<char *const *>(array_orig);

  auto retval = load_p4_main(l.size(), array, run_midend);

  delete [] array;

  return retval;
}

const IR::P4Program* load_p4_simple(std::string filename, std::string include_dir, bool run_midend) {
    const int argc = 4;
    char const* args[argc];
    args[0] = "p4c";
    args[1] = filename.c_str();
    args[2] = "-I";
    args[3] = include_dir.c_str();
    return load_p4_main(argc, const_cast<char *const *>(args), run_midend);
}


class NodeVisitor : public Inspector {
    typedef std::function<bool(IR::Node*)> nodefun;

    nodefun fun_pre;
    nodefun fun_post;

 public:
    explicit NodeVisitor(nodefun fun_pre, nodefun fun_post) : fun_pre(fun_pre), fun_post(fun_post) {}
    bool preorder(const IR::Node* node) override {
        return fun_pre(const_cast<IR::Node*>(node));
    }

    void postorder(const IR::Node* node) override {
        fun_post(const_cast<IR::Node*>(node));
    }
};


void test_visitor(const IR::P4Program* program, boost::python::object fun) {
    auto fun_pre = [&fun](IR::Node* node) -> bool {
        return boost::python::extract<bool>(fun.attr("fun_pre")(boost::ref(node)));
    };

    auto fun_post = [&fun](IR::Node* node) -> bool {
        return boost::python::extract<bool>(fun.attr("fun_post")(boost::ref(node)));
    };

    NodeVisitor visitor(fun_pre, fun_post);
    program->apply(visitor);
}

std::string cstring_to_stdstring(cstring& cstring) {
    std::string s(cstring);
    return s;
}


BOOST_PYTHON_MODULE(p4c) {
    using namespace boost::python;

    class_<cstring>("cstring")
    ;

    class_<IR::Node, boost::noncopyable>("IR_Node", no_init)
    ;

    def("load_p4", &load_p4, return_internal_reference<>());
    def("load_p4_simple", &load_p4_simple, return_internal_reference<>());

    def("cstring_to_stdstring", &cstring_to_stdstring);
    def("test_visitor", &test_visitor, return_internal_reference<>());

#ifdef P4C_BOOST_MODULE
#include BOOST_PP_STRINGIZE(P4C_BOOST_MODULE)
#else
#include "p4c.cpp.boosted"
#endif
}
