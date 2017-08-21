#!/bin/sh
set -xe

SPECFILE=$1

err() {
  exitval="$1"
  shift
  echo "$@" > /dev/stderr
  exit $exitval
}

echo "Building \"$1\""
if [ ! -f "$1" ]; then
  err 1 "Spec \"$1\" not found"
fi

shift

GIT_VERSION="$(git rev-list HEAD -n 1)"
BRANCH="$(git name-rev --name-only HEAD)"
PACKAGER="$(git config user.name) <$(git config user.email)>"
CURRENT_DATETIME=`date +'%Y%m%d%H%M%S'`

if [ ! -f "$HOME/.rpmmacros" ]; then
   echo "%_topdir $HOME/rpm/" > $HOME/.rpmmacros
   echo "%_tmppath $HOME/rpm/tmp" >> $HOME/.rpmmacros
   echo "%packager ${PACKAGER}" >> $HOME/.rpmmacros

fi

if [ ! -d "$HOME/rpm" ]; then
  echo "Creating directories need by rpmbuild"
  mkdir -p ~/rpm/{BUILD,RPMS,SOURCES,SRPMS,SPECS,tmp} 2>/dev/null
  mkdir ~/rpm/RPMS/{i386,i586,i686,noarch} 2>/dev/null
fi

RPM_TOPDIR=`rpm --eval '%_topdir'`
BUILDROOT=`rpm --eval '%_tmppath'`
BUILDROOT_TMP="$BUILDROOT/tmp/"
BUILDROOT="$BUILDROOT/tmp/${PACKAGE}"


mkdir -p ${RPM_TOPDIR}/{BUILD,RPMS,SOURCES,SRPMS,SPECS}
mkdir -p ${RPM_TOPDIR}/RPMS/{i386,i586,i686,noarch}
mkdir -p $BUILDROOT

git archive --format=tar --prefix=otus-${CURRENT_DATETIME}/ ${BRANCH} | gzip > ${RPM_TOPDIR}/SOURCES/otus-${CURRENT_DATETIME}.tar.gz

echo '############################################################'
rpmbuild -ba --clean $SPECFILE \
  --define "current_datetime ${CURRENT_DATETIME}" \
  --define "git_version ${GIT_VERSION}" \
  --define "git_branch ${BRANCH}"
