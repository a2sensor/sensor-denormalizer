# flake.nix
#
# This file packages a2sensor/sensor-denormalizer as a Nix flake.
#
# Copyright (C) 2023-today a2sensor's a2sensor/sensor-denormalizer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
{
  description = "A Python denormalizer for a2sensor/sensor-denormalizer";
  inputs = rec {
    flake-utils.url = "github:numtide/flake-utils/v1.0.0";
    nixos.url = "github:NixOS/nixpkgs/nixos-23.05";
    pythoneda-shared-pythoneda-banner = {
      inputs.flake-utils.follows = "flake-utils";
      inputs.nixos.follows = "nixos";
      url = "github:pythoneda-shared-pythoneda/banner/0.0.8";
    };
    pythoneda-shared-pythoneda-domain = {
      inputs.flake-utils.follows = "flake-utils";
      inputs.nixos.follows = "nixos";
      inputs.pythoneda-shared-pythoneda-banner.follows =
        "pythoneda-shared-pythoneda-banner";
      url =
        "github:pythoneda-shared-pythoneda/domain-artifact/0.0.9?dir=domain";
    };
  };
  outputs = inputs:
    with inputs;
    let
      defaultSystems = flake-utils.lib.defaultSystems;
      supportedSystems = if builtins.elem "armv6l-linux" defaultSystems then
        defaultSystems
      else
        defaultSystems ++ [ "armv6l-linux" ];
    in flake-utils.lib.eachSystem supportedSystems (system:
      let
        org = "a2sensor";
        repo = "sensor-denormalizer";
        version = "0.0.6";
        pname = "${org}-${repo}";
        pkgs = import nixos { inherit system; };
        description = "A Python denormalizer for a2sensor/sensor-denormalizer";
        license = pkgs.lib.licenses.gpl3;
        homepage = "https://github.com/a2sensor/sensor-denormalizer";
        maintainers = [ "rydnr <github@acm-sl.org>" ];
        archRole = "B";
        space = "D";
        layer = "A";
        pythonpackage = "a2sensor.sensor_denormalizer";
        package = builtins.replaceStrings [ "." ] [ "/" ] pythonpackage;
        entrypoint = "denormalizer";
        nixosVersion = builtins.readFile "${nixos}/.version";
        nixpkgsRelease =
          builtins.replaceStrings [ "\n" ] [ "" ] "nixos-${nixosVersion}";
        shared = import "${pythoneda-shared-pythoneda-banner}/nix/shared.nix";
        a2sensor-sensor-denormalizer-for =
          { python, pythoneda-shared-pythoneda-banner }:
          let
            pnameWithUnderscores =
              builtins.replaceStrings [ "-" ] [ "_" ] pname;
            pythonVersionParts = builtins.splitVersion python.version;
            pythonMajorVersion = builtins.head pythonVersionParts;
            pythonMajorMinorVersion =
              "${pythonMajorVersion}.${builtins.elemAt pythonVersionParts 1}";
            wheelName =
              "${pnameWithUnderscores}-${version}-py${pythonMajorVersion}-none-any.whl";
            banner_file = "${package}/denormalizer_banner.py";
            banner_class = "DenormalizerBanner";
          in python.pkgs.buildPythonPackage rec {
            inherit pname version;
            projectDir = ./.;
            pyprojectTemplateFile = ./pyprojecttoml.template;
            pyprojectTemplate = pkgs.substituteAll {
              authors = builtins.concatStringsSep ","
                (map (item: ''"${item}"'') maintainers);
              desc = description;
              inherit homepage pname pythonMajorMinorVersion pythonpackage
                version;
              package = builtins.replaceStrings [ "." ] [ "/" ] pythonpackage;
              pythonedaSharedPythonedaBanner =
                pythoneda-shared-pythoneda-banner.version;
              src = pyprojectTemplateFile;
              toml = python.pkgs.toml.version;
            };
            bannerTemplateFile = ./templates/banner.py.template;
            bannerTemplate = pkgs.substituteAll {
              project_name = pname;
              file_path = banner_file;
              inherit banner_class org repo;
              tag = version;
              pescio_space = space;
              arch_role = archRole;
              hexagonal_layer = layer;
              python_version = pythonMajorMinorVersion;
              nixpkgs_release = nixpkgsRelease;
              src = bannerTemplateFile;
            };

            entrypointTemplateFile = ./templates/entrypoint.sh.template;
            entrypointTemplate = pkgs.substituteAll {
              arch_role = archRole;
              gunicorn = python.pkgs.gunicorn;
              hexagonal_layer = layer;
              nixpkgs_release = nixpkgsRelease;
              inherit homepage maintainers org python repo version;
              pescio_space = space;
              python_version = pythonMajorMinorVersion;
              pythoneda_shared_pythoneda_banner =
                pythoneda-shared-pythoneda-banner;
              pythoneda_shared_pythoneda_domain =
                pythoneda-shared-pythoneda-domain;
              src = entrypointTemplateFile;
            };
            src = ./.;

            format = "pyproject";

            nativeBuildInputs = with python.pkgs; [ pip pkgs.jq poetry-core ];
            propagatedBuildInputs = with python.pkgs; [
              pythoneda-shared-pythoneda-banner
              toml
            ];

            pythonImportsCheck = [ pythonpackage ];

            unpackPhase = ''
              cp -r ${src} .
              sourceRoot=$(ls | grep -v env-vars)
              chmod -R +w $sourceRoot
              cp ${pyprojectTemplate} $sourceRoot/pyproject.toml
              cp ${entrypointTemplate} $sourceRoot/entrypoint.sh
              cp ${bannerTemplate} $sourceRoot/${banner_file}
            '';

            postPatch = ''
              substituteInPlace /build/$sourceRoot/entrypoint.sh \
                --replace "@SOURCE@" "$out/bin/${entrypoint}.sh" \
                --replace "@PYTHONPATH@" "$PYTHONPATH" \
                --replace "@ENTRYPOINT@" "-m ${pythonpackage}.${entrypoint}" \
                --replace "@BANNER@" "$out/bin/banner.sh"
            '';

            postInstall = ''
              pushd /build/$sourceRoot
              for f in $(find . -name '__init__.py'); do
                if [[ ! -e $out/lib/python${pythonMajorMinorVersion}/site-packages/$f ]]; then
                  cp $f $out/lib/python${pythonMajorMinorVersion}/site-packages/$f;
                fi
              done
              popd
              mkdir $out/dist $out/bin
              cp dist/${wheelName} $out/dist
              jq ".url = \"$out/dist/${wheelName}\"" $out/lib/python${pythonMajorMinorVersion}/site-packages/${pnameWithUnderscores}-${version}.dist-info/direct_url.json > temp.json && mv temp.json $out/lib/python${pythonMajorMinorVersion}/site-packages/${pnameWithUnderscores}-${version}.dist-info/direct_url.json
              cp /build/$sourceRoot/entrypoint.sh $out/bin/${entrypoint}.sh
              chmod +x $out/bin/${entrypoint}.sh
              echo '#!/usr/bin/env sh' > $out/bin/banner.sh
              echo "export PYTHONPATH=$PYTHONPATH" >> $out/bin/banner.sh
              echo "${python}/bin/python $out/lib/python${pythonMajorMinorVersion}/site-packages/${banner_file} \$@" >> $out/bin/banner.sh
              chmod +x $out/bin/banner.sh
            '';

            meta = with pkgs.lib; {
              inherit description homepage license maintainers;
            };
          };
      in rec {
        apps = rec {
          default = a2sensor-sensor-denormalizer-default;
          a2sensor-sensor-denormalizer-default =
            a2sensor-sensor-denormalizer-python311;
          a2sensor-sensor-denormalizer-python38 = shared.app-for rec {
            package =
              self.packages.${system}.a2sensor-sensor-denormalizer-python38;
            inherit entrypoint;
          };
          a2sensor-sensor-denormalizer-python39 = shared.app-for rec {
            package =
              self.packages.${system}.a2sensor-sensor-denormalizer-python39;
            inherit entrypoint;
          };
          a2sensor-sensor-denormalizer-python310 = shared.app-for rec {
            package =
              self.packages.${system}.a2sensor-sensor-denormalizer-python310;
            inherit entrypoint;
          };
          a2sensor-sensor-denormalizer-python311 = shared.app-for rec {
            package =
              self.packages.${system}.a2sensor-sensor-denormalizer-python311;
            inherit entrypoint;
          };
        };
        defaultPackage = packages.default;
        devShells = rec {
          default = a2sensor-sensor-denormalizer-default;
          a2sensor-sensor-denormalizer-default =
            a2sensor-sensor-denormalizer-python311;
          a2sensor-sensor-denormalizer-python38 = shared.devShell-for {
            banner =
              "${packages.a2sensor-sensor-denormalizer-python38}/bin/banner.sh";
            package = packages.a2sensor-sensor-denormalizer-python38;
            python = pkgs.python38;
            pythoneda-shared-pythoneda-banner =
              pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python38;
            pythoneda-shared-pythoneda-domain =
              pythoneda-shared-pythoneda-domain.packages.${system}.pythoneda-shared-pythoneda-domain-python38;
            inherit archRole layer nixpkgsRelease org pkgs repo space;
          };
          a2sensor-sensor-denormalizer-python39 = shared.devShell-for {
            banner =
              "${packages.a2sensor-sensor-denormalizer-python39}/bin/banner.sh";
            package = packages.a2sensor-sensor-denormalizer-python39;
            python = pkgs.python39;
            pythoneda-shared-pythoneda-banner =
              pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python39;
            pythoneda-shared-pythoneda-domain =
              pythoneda-shared-pythoneda-domain.packages.${system}.pythoneda-shared-pythoneda-domain-python39;
            inherit archRole layer nixpkgsRelease org pkgs repo space;
          };
          a2sensor-sensor-denormalizer-python310 = shared.devShell-for {
            banner =
              "${packages.a2sensor-sensor-denormalizer-python310}/bin/banner.sh";
            package = packages.a2sensor-sensor-denormalizer-python310;
            python = pkgs.python310;
            pythoneda-shared-pythoneda-banner =
              pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python310;
            pythoneda-shared-pythoneda-domain =
              pythoneda-shared-pythoneda-domain.packages.${system}.pythoneda-shared-pythoneda-domain-python310;
            inherit archRole layer nixpkgsRelease org pkgs repo space;
          };
          a2sensor-sensor-denormalizer-python311 = shared.devShell-for {
            banner =
              "${packages.a2sensor-sensor-denormalizer-python311}/bin/banner.sh";
            package = packages.a2sensor-sensor-denormalizer-python311;
            python = pkgs.python311;
            pythoneda-shared-pythoneda-banner =
              pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python311;
            pythoneda-shared-pythoneda-domain =
              pythoneda-shared-pythoneda-domain.packages.${system}.pythoneda-shared-pythoneda-domain-python311;
            inherit archRole layer nixpkgsRelease org pkgs repo space;
          };
        };
        packages = rec {
          default = a2sensor-sensor-denormalizer-default;
          a2sensor-sensor-denormalizer-default =
            a2sensor-sensor-denormalizer-python311;
          a2sensor-sensor-denormalizer-python38 =
            a2sensor-sensor-denormalizer-for {
              python = pkgs.python38;
              pythoneda-shared-pythoneda-banner =
                pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python38;
            };
          a2sensor-sensor-denormalizer-python39 =
            a2sensor-sensor-denormalizer-for {
              python = pkgs.python39;
              pythoneda-shared-pythoneda-banner =
                pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python39;
            };
          a2sensor-sensor-denormalizer-python310 =
            a2sensor-sensor-denormalizer-for {
              python = pkgs.python310;
              pythoneda-shared-pythoneda-banner =
                pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python310;
            };
          a2sensor-sensor-denormalizer-python311 =
            a2sensor-sensor-denormalizer-for {
              python = pkgs.python311;
              pythoneda-shared-pythoneda-banner =
                pythoneda-shared-pythoneda-banner.packages.${system}.pythoneda-shared-pythoneda-banner-python311;
            };
        };
      });
}
