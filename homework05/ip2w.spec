License:        BSD
Vendor:         Otus
Group:          PD01
URL:            http://otus.ru/lessons/3/
Source0:        otus-%{current_datetime}.tar.gz
BuildRoot:      %{_tmppath}/otus-%{current_datetime}
Name:           ip2w
Version:        0.0.1
Release:        1
BuildArch:      noarch
BuildRoot:      %{_tmppath}/%{name}-root
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
BuildRequires: systemd
Requires: python
Requires: python-requests
Summary: Example of uWSGI daemon


%description
Get weather by IPv4 address

Git version: %{git_version} (branch: %{git_branch})

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

%define __etcdir    /usr/local/etc
%define __logdir    /var/log/
%define __bindir    /usr/local/ip2w/
%define __systemddir	/usr/lib/systemd/system/

%prep
rm -rf %{buildroot}
%setup -n otus-%{current_datetime}

%install
[ "%{buildroot}" != "/" ] && rm -fr %{buildroot}

%{__mkdir} -p %{buildroot}/%{__bindir}
%{__mkdir} -p %{buildroot}/%{__etcdir}
%{__mkdir} -p %{buildroot}/%{__systemddir}
%{__mkdir} -p %{buildroot}/%{__logdir}

%{__install} -pD -m 644 %{name}.service %{buildroot}/%{__systemddir}/%{name}.service
%{__install} -pD -m 755 %{name}.py %{buildroot}/%{__bindir}/%{name}.py
%{__install} -pD -m 644 %{name}.ini %{buildroot}/%{__etcdir}/%{name}.ini

%post
%systemd_post %{name}.service
systemctl daemon-reload

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun %{name}.service

%clean
[ "%{buildroot}" != "/" ] && rm -fr %{buildroot}

%files
%{__logdir}
%{__bindir}
%{__systemddir}
%{__etcdir}
