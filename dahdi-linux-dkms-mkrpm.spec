%{?!module_name: %{error: You did not specify a module name (%%module_name)}}
%{?!version: %{error: You did not specify a module version (%%version)}}
%{?!kernel_versions: %{error: You did not specify kernel versions (%%kernel_version)}}
%{?!packager: %define packager DKMS <dkms-devel@lists.us.dell.com>}
%{?!license: %define license Unknown}
%{?!_dkmsdir: %define _dkmsdir /var/lib/dkms}
%{?!_srcdir: %define _srcdir %_prefix/src}
%{?!_datarootdir: %define _datarootdir %{_datadir}}

Summary:	%{module_name} %{version} dkms package
Name:		%{module_name}
Version:	%{version}
License:	%license
Release:	6dkms
BuildArch:	noarch
Group:		System/Kernel
Requires: 	dkms >= 1.95
Obsoletes:     dahdi-linux < 2.11.1
Provides:      dahdi-linux = 2.11.1-5dkms
Requires:      dkms >= 1.95
Requires:      dahdi = 2.11.1
Requires:      dahdi-tools = 2.11.1
Requires:      /bin/sh
Requires:      wget
Requires:      /bin/bash
Requires:      /bin/sh
Requires:      /bin/true
Requires:      /usr/bin/perl
Requires:      /usr/bin/php
Requires:      perl(File::Basename)
Requires:      perl(Getopt::Std)
Requires:      perl(XppConfig)
Requires:      perl(strict)
BuildRequires: 	dkms
BuildRoot: 	%{_tmppath}/%{name}-%{version}-%{release}-root/

%description
Kernel modules for %{module_name} %{version} in a DKMS wrapper.

%prep
if [ "%mktarball_line" != "none" ]; then
        /usr/sbin/dkms mktarball -m %module_name -v %version %mktarball_line --archive `basename %{module_name}-%{version}.dkms.tar.gz`
        cp -af %{_dkmsdir}/%{module_name}/%{version}/tarball/`basename %{module_name}-%{version}.dkms.tar.gz` %{module_name}-%{version}.dkms.tar.gz
fi

%install
if [ "$RPM_BUILD_ROOT" != "/" ]; then
        rm -rf $RPM_BUILD_ROOT
fi
mkdir -p $RPM_BUILD_ROOT/%{_srcdir}
mkdir -p $RPM_BUILD_ROOT/%{_datarootdir}/%{module_name}

if [ -d %{_sourcedir}/%{module_name}-%{version} ]; then
        cp -Lpr %{_sourcedir}/%{module_name}-%{version} $RPM_BUILD_ROOT/%{_srcdir}
fi

if [ -f %{module_name}-%{version}.dkms.tar.gz ]; then
        install -m 644 %{module_name}-%{version}.dkms.tar.gz $RPM_BUILD_ROOT/%{_datarootdir}/%{module_name}
fi

if [ -f %{_sourcedir}/common.postinst ]; then
        install -m 755 %{_sourcedir}/common.postinst $RPM_BUILD_ROOT/%{_datarootdir}/%{module_name}/postinst
fi

%clean
if [ "$RPM_BUILD_ROOT" != "/" ]; then
        rm -rf $RPM_BUILD_ROOT
fi

%pre
echo -e "PLEASE BE PATIENT ..."
echo -e "... THIS WILL TAKE LONG ..."
echo -e "####   GO GRAB SOME COFFEE   ####"
echo -e "        .."
echo -e "      ..  .."
echo -e "            .."
echo -e "             .."
echo -e "            .."
echo -e "           .."
echo -e "         .."
echo -e "##       ..    ####"
echo -e "##...............##  ##"
echo -e "##....o..o..o....##   ##"
echo -e "##....o..o..o....## ##"
echo -e "##....o..o..o....###"
echo -e " ##......o......##"
echo -e "  #############"
echo -e "  ###ISSABEL###"
echo -e "#################"

%post
if [ "$(modinfo -F version dahdi)" != "2.11.1" ]; then dkms uninstall -m dahdi-linux -v 2.11.1 -q; dkms install -m dahdi-linux -v 2.11.1 -q --force; fi
if dkms status | grep dahdi-linux | grep 2.11.1 | grep added; then sed -i 's/KSRC/-j1 KSRC/g' /usr/src/dahdi-linux-2.11.1/dkms.conf; dkms install -m dahdi-linux -v 2.11.1 -q --force;fi
for POSTINST in %{_prefix}/lib/dkms/common.postinst %{_datarootdir}/%{module_name}/postinst; do
        if [ -f $POSTINST ]; then
                $POSTINST %{module_name} %{version} %{_datarootdir}/%{module_name}
                exit $?
        fi
        echo "WARNING: $POSTINST does not exist."
done
echo -e "ERROR: DKMS version is too old and %{module_name} was not"
echo -e "built with legacy DKMS support."
echo -e "You must either rebuild %{module_name} with legacy postinst"
echo -e "support or upgrade DKMS to a more current version."
exit 1

%preun
echo -e
echo -e "Uninstall of %{module_name} module (version %{version}) beginning:"
dkms remove -m %{module_name} -v %{version} --all --rpm_safe_upgrade
exit 0

%triggerpostun -- dahdi-linux
if [ -d /usr/src/dahdi-linux-2.11.1 ]
then
        echo -e "Check if modules are installed..."
        if dkms status | grep dahdi-linux | grep installed
        then
                echo -e "OK"
        else
                echo -e "Fail, reinstalling..."
                dkms add -m dahdi-linux -v 2.11.1
                dkms install -m dahdi-linux -v 2.11.1
        fi
fi
if dkms status | grep dahdi-linux | grep 2.11.1 | grep Diff; then dkms uninstall -m dahdi-linux -v 2.11.1 -q; dkms install -m dahdi-linux -v 2.11.1 -q --force; systemctl restart dahdi; fi
if dkms status | grep dahdi-linux | grep 2.11.1 | grep added; then sed -i 's/KSRC/-j1 KSRC/g' /usr/src/dahdi-linux-2.11.1/dkms.conf; dkms install -m dahdi-linux -v 2.11.1 -q --force;fi
systemctl restart dahdi
exit 0

%files
%defattr(-,root,root)
%{_srcdir}
%{_datarootdir}/%{module_name}/

%changelog
* %(date "+%a %b %d %Y") %packager %{version}-%{release}
- Automatic build by DKMS

