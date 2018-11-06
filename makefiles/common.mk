# Copyright 2016 Eotvos Lorand University, Budapest, Hungary
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

CFLAGS += -O3
CFLAGS += -Wall 
CFLAGS += -Wno-unused-function
CFLAGS += -Wno-unused-but-set-variable
CFLAGS += -Wno-unused-variable
CFLAGS += -g
CFLAGS += -std=gnu11
CFLAGS += -I "$(CDIR)/../../hardware_dep/shared/includes"

CFLAGS += -I "$(CDIR)/srcgen"
VPATH  += $(CDIR)/srcgen

# P4Runtime support
GRPCDIR = "$(CDIR)/../../../../grpc-c/build"
P4RTDIR = "$(CDIR)/../../../../P4RuntimeAPI"
PIDIR = "$(CDIR)/../../../../PI"

CFLAGS += -I "$(P4RTDIR)"
CFLAGS += -I "$(GRPCDIR)/lib/h"
CFLAGS += -I "$(GRPCDIR)/third_party/protobuf-c"
CFLAGS += -I "$(GRPCDIR)/third_party/grpc/include"
CFLAGS += -I "$(P4RTDIR)/grpc-c-out"
CFLAGS += -I "$(P4RTDIR)/include"
CFLAGS += -I "$(PIDIR)/proto/server"
# end of P4Runtime support

ifneq ($(P4_GCC_OPTS),)
CFLAGS += $(P4_GCC_OPTS)
endif

SRCS-y += util.c
