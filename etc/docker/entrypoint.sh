#!/bin/bash

set -eux

creme migrate;
creme creme_populate;
creme generatemedia;
creme check;

$@
