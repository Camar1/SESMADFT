function ResultsTable = ses_calculate_all_panels_from_single_probe(filename, sheetName, opts)
%==========================================================================
% SES CALCULATOR - SINGLE PROBE -> ALL PANEL CALCULATIONS
%==========================================================================
% Reads one Excel file with one specimen/probe and the same structure as
% your sheet:
%   - metadata block
%   - TEST DATA block with LOAD and Displacement
%
% It does NOT identify the probe as one panel.
% It computes the results for ALL panel types:
%   FBH, FHB, FBHS, SHB, MHBS, SISv, SISh
%
% 3PBT:
%   - finds x1, x2, y1, y2 for maximum slope with dx >= 1 mm
%   - gets slope, intercept, max force
%   - plots the clean graph
%   - computes all SES results for all panel types
%
% Shear:
%   - finds highest and lowest peaks sufficiently separated
%   - plots the clean graph
%   - computes shear results for all panel types
%
% Output formatting:
%   - decimal commas
%   - no File / Sheet columns
%
%==========================================================================
% EXAMPLES
%--------------------------------------------------------------------------
% T = ses_calculate_all_panels_from_single_probe('probe.xlsx');
%
% opts = struct;
% opts.plotFigure = true;
% opts.exportSummaryExcel = true;
% T = ses_calculate_all_panels_from_single_probe('probe.xlsx', '', opts);
%==========================================================================

    if nargin < 2 || isempty(sheetName)
        sh = sheetnames(filename);
        sheetName = sh{1};
    end
    if nargin < 3
        opts = struct();
    end
    opts = fillDefaultOpts(opts);

    raw = readcell(filename, 'Sheet', sheetName, 'UseExcel', false);

    meta = extractMetadata(raw);
    [x_mm, y_N] = extractLoadDisplacement(raw);

    if numel(x_mm) < 3
        error('Not enough load-displacement points found.');
    end

    panelCodes = ["FBH","FHB","FBHS","SHB","MHBS","SISv","SISh"];

    lam = parseLaminateExactlyAsWorkbook(meta.Laminate, opts);

    base = struct();
    base.Metadata = meta;
    base.LaminateInfo = lam;
    base.Data.displacement_mm = x_mm(:);
    base.Data.load_N = y_N(:);
    base.MaxForce_N = max(y_N);

    testType = upper(strtrim(string(meta.Type)));
    rows = {};

    fprintf('\n====================================================\n');
    fprintf('SES SINGLE PROBE -> ALL PANEL CALCULATIONS\n');
    fprintf('Type : %s\n', meta.Type);
    fprintf('====================================================\n');

    if contains(testType, "3PBT") || contains(testType, "3PB")

        common3PB = compute3PBCommon(base, opts);

        if opts.plotFigure
            plot3PB_clean(base, common3PB);
        end

        for k = 1:numel(panelCodes)
            code = panelCodes(k);
            r = base;
            r.Mode = "3PBT";
            r.PanelCode = code;
            r.LinearRegion = common3PB.LinearRegion;
            r.MaxForce_N = common3PB.MaxForce_N;
            r = compute3PBAllWorkbookFormulas(r, code, opts);
            rows{end+1,1} = resultToRowFormatted(r); %#ok<AGROW>
            printSummary(r);
        end

    elseif contains(testType, "SHEAR")

        commonShear = computeShearCommon(base, opts);

        if opts.plotFigure
            plotShear_clean(base, commonShear);
        end

        for k = 1:numel(panelCodes)
            code = panelCodes(k);
            r = base;
            r.Mode = "Shear";
            r.PanelCode = code;
            r.Shear = commonShear.Shear;
            r = computeShearAllWorkbookFormulas(r, code);
            rows{end+1,1} = resultToRowFormatted(r); %#ok<AGROW>
            printSummary(r);
        end

    else
        error('Unsupported Type "%s". Supported: 3PBT / 3PB / Shear.', meta.Type);
    end

    ResultsTable = vertcat(rows{:});

    if opts.exportSummaryExcel
        [folder, baseName, ~] = fileparts(filename);
        if isempty(folder)
            folder = pwd;
        end
        outFile = fullfile(folder, [baseName '_ALL_PANEL_RESULTS.xlsx']);
        writetable(ResultsTable, outFile, 'Sheet', 'Summary');
        fprintf('\nSummary exported to: %s\n', outFile);
    end
end

%==========================================================================
% DEFAULT OPTIONS
%==========================================================================
function opts = fillDefaultOpts(opts)
    if ~isfield(opts, 'span_mm'),                opts.span_mm = 400; end
    if ~isfield(opts, 'specimenWidth_mm'),       opts.specimenWidth_mm = 500; end
    if ~isfield(opts, 'specimenLength_mm'),      opts.specimenLength_mm = 275; end
    if ~isfield(opts, 'minSlopeDx_mm'),          opts.minSlopeDx_mm = 1.0; end
    if ~isfield(opts, 'minPeakDistance_mm'),     opts.minPeakDistance_mm = []; end
    if ~isfield(opts, 'peakProminenceFraction'), opts.peakProminenceFraction = 0.08; end
    if ~isfield(opts, 'plotFigure'),             opts.plotFigure = true; end
    if ~isfield(opts, 'exportSummaryExcel'),     opts.exportSummaryExcel = false; end
end

%==========================================================================
% METADATA EXTRACTION
%==========================================================================
function meta = extractMetadata(raw)
    meta = struct( ...
        'SpecimenID', "", ...
        'Type', "", ...
        'Date', "", ...
        'CFType', "", ...
        'Laminate', "", ...
        'CoreMaterial', "", ...
        'CoreThickness_mm', NaN, ...
        'Height_mm', NaN, ...
        'Width_mm', NaN, ...
        'Thickness_mm', NaN, ...
        'Weight_g', NaN, ...
        'SkinThickness_mm', NaN);

    labels = string(raw);

    meta.Type             = getValueByLabel(raw, labels, "Type");
    meta.Date             = getValueByLabel(raw, labels, "Date");
    meta.CFType           = getValueByLabel(raw, labels, "CF type");
    meta.Laminate         = getValueByLabel(raw, labels, "Laminate");
    meta.CoreMaterial     = getValueByLabel(raw, labels, "Core material");
    meta.CoreThickness_mm = toNumber(getValueByLabel(raw, labels, "Core Thickness (mm)"));
    meta.Height_mm        = toNumber(getValueByLabel(raw, labels, "Height (mm)"));
    meta.Width_mm         = toNumber(getValueByLabel(raw, labels, "Width (mm)"));
    meta.Thickness_mm     = toNumber(getValueByLabel(raw, labels, "Thickness (mm)"));
    meta.Weight_g         = toNumber(getValueByLabel(raw, labels, "Weight (g)"));
    meta.SkinThickness_mm = toNumber(getValueByLabel(raw, labels, "Skin thickness (mm)"));

    for r = 1:min(6,size(raw,1))
        for c = 1:size(raw,2)
            v = raw{r,c};
            if ischar(v) || isstring(v)
                s = strtrim(string(v));
                if ~isempty(regexp(s, '^\d{4}-P\d{2}-\d{2}', 'once'))
                    meta.SpecimenID = s;
                    return;
                end
            end
        end
    end
end

function value = getValueByLabel(raw, labels, labelText)
    value = "";
    [rr, cc] = find(strcmpi(strtrim(labels), string(labelText)), 1, 'first');
    if isempty(rr)
        return;
    end

    if cc < size(raw,2)
        value = cellToString(raw{rr,cc+1});
        if strlength(strtrim(value)) > 0
            return;
        end
    end

    for c = cc+1:size(raw,2)
        s = cellToString(raw{rr,c});
        if strlength(strtrim(s)) > 0
            value = s;
            return;
        end
    end
end

%==========================================================================
% LOAD / DISPLACEMENT EXTRACTION
%==========================================================================
function [x_mm, y_N] = extractLoadDisplacement(raw)
    x_mm = [];
    y_N = [];

    labels = string(raw);
    testDataRow = find(any(strcmpi(strtrim(labels), "TEST DATA"), 2), 1, 'first');
    if isempty(testDataRow)
        error('TEST DATA block not found.');
    end

    headerRow = testDataRow;
    [~, loadCol] = find(strcmpi(strtrim(string(raw(headerRow,:))), "LOAD"), 1, 'first');
    [~, dispCol] = find(strcmpi(strtrim(string(raw(headerRow,:))), "Displacement"), 1, 'first');

    if isempty(loadCol) || isempty(dispCol)
        headerRow = testDataRow + 1;
        [~, loadCol] = find(strcmpi(strtrim(string(raw(headerRow,:))), "LOAD"), 1, 'first');
        [~, dispCol] = find(strcmpi(strtrim(string(raw(headerRow,:))), "Displacement"), 1, 'first');
    end

    if isempty(loadCol) || isempty(dispCol)
        error('LOAD / Displacement columns not found.');
    end

    r = headerRow + 1;
    while r <= size(raw,1)
        lv = raw{r,loadCol};
        xv = raw{r,dispCol};

        if isBlankCell(lv) && isBlankCell(xv)
            break;
        end

        y = toNumber(lv);
        x = toNumber(xv);

        if ~isnan(x) && ~isnan(y)
            x_mm(end+1,1) = x; %#ok<AGROW>
            y_N(end+1,1) = y; %#ok<AGROW>
        end
        r = r + 1;
    end

    good = isfinite(x_mm) & isfinite(y_N);
    x_mm = x_mm(good);
    y_N = y_N(good);

    [x_mm, idx] = sort(x_mm);
    y_N = y_N(idx);

    [x_mm, ia] = unique(x_mm, 'stable');
    y_N = y_N(ia);
end

function tf = isBlankCell(v)
    if isempty(v)
        tf = true;
    elseif isstring(v)
        tf = strlength(strtrim(v)) == 0;
    elseif ischar(v)
        tf = isempty(strtrim(v));
    elseif ismissing(v)
        tf = true;
    else
        tf = false;
    end
end

%==========================================================================
% LAMINATE PARSING EXACTLY AS WORKBOOK
%==========================================================================
function lam = parseLaminateExactlyAsWorkbook(laminateText, opts)
    lam = struct();
    lam.Raw = string(laminateText);

    clean = upper(strtrim(string(laminateText)));
    clean = replace(clean, "[", "");
    clean = replace(clean, "]", "");
    clean = replace(clean, " S.", "");
    clean = replace(clean, "S.", "");
    clean = strtrim(clean);

    if strlength(clean) == 0
        tokens = strings(0,1);
    else
        tokens = split(clean, "/");
        tokens = strtrim(tokens);
        tokens = tokens(tokens ~= "");
    end

    n = numel(tokens);

    orientation = strings(n,1);
    thickness_mm = zeros(n,1);
    fiberWeight_g = zeros(n,1);   % Excel column E
    totalWeight_g = zeros(n,1);   % Excel column F
    zeroFiber_g   = zeros(n,1);   % Excel column G

    area_m2 = (opts.specimenWidth_mm*0.001) * (opts.specimenLength_mm*0.001);

    for i = 1:n
        t = string(tokens(i));

        if t == "+-45"
            orientation(i) = "RC +-45º";
            thickness_mm(i) = 0.44;
            fiberWeight_g(i) = area_m2 * 416;
            totalWeight_g(i) = fiberWeight_g(i) / (1 - 0.4);
            zeroFiber_g(i)   = fiberWeight_g(i) * 0.0;

        elseif t == "+-90"
            orientation(i) = "RC +-90º";
            thickness_mm(i) = 0.44;
            fiberWeight_g(i) = area_m2 * 416;
            totalWeight_g(i) = fiberWeight_g(i) / (1 - 0.4);
            zeroFiber_g(i)   = fiberWeight_g(i) * 0.5;

        elseif t == "0"
            orientation(i) = "UD 0º";
            thickness_mm(i) = 0.30;
            fiberWeight_g(i) = area_m2 * 300;
            totalWeight_g(i) = fiberWeight_g(i) / (1 - 0.35);
            zeroFiber_g(i)   = fiberWeight_g(i) * 1.0;

        elseif t == "+45"
            orientation(i) = "UD +45º";
            thickness_mm(i) = 0.30;
            fiberWeight_g(i) = area_m2 * 300;
            totalWeight_g(i) = fiberWeight_g(i) / (1 - 0.35);
            zeroFiber_g(i)   = 0;

        elseif t == "-45"
            orientation(i) = "UD -45º";
            thickness_mm(i) = 0.30;
            fiberWeight_g(i) = area_m2 * 300;
            totalWeight_g(i) = fiberWeight_g(i) / (1 - 0.35);
            zeroFiber_g(i)   = 0;

        elseif t == "90"
            orientation(i) = "UD 90º";
            thickness_mm(i) = 0.30;
            fiberWeight_g(i) = area_m2 * 300;
            totalWeight_g(i) = fiberWeight_g(i) / (1 - 0.35);
            zeroFiber_g(i)   = 0;

        elseif t == "XC +-45" || t == "XC+-45" || t == "XC"
            orientation(i) = "XC +-45º";
            thickness_mm(i) = 0.60;
            fiberWeight_g(i) = area_m2 * 416;
            totalWeight_g(i) = fiberWeight_g(i);
            zeroFiber_g(i)   = 0;

        elseif t == "XC +-90" || t == "XC+-90"
            orientation(i) = "XC +-90º";
            thickness_mm(i) = 0.60;
            fiberWeight_g(i) = area_m2 * 416;
            totalWeight_g(i) = fiberWeight_g(i);
            zeroFiber_g(i)   = fiberWeight_g(i) * 0.5;

        else
            orientation(i) = t;
            thickness_mm(i) = 0;
            fiberWeight_g(i) = 0;
            totalWeight_g(i) = 0;
            zeroFiber_g(i) = 0;
        end
    end

    lam.HalfStack = orientation;
    lam.NumHalfPlies = n;
    lam.NumTotalPlies = 2*n;
    lam.ThicknessPerPly_mm = thickness_mm;
    lam.FiberWeightPerPly_g = fiberWeight_g;
    lam.TotalWeightPerPly_g = totalWeight_g;
    lam.ZeroFiberPerPly_g = zeroFiber_g;

    % EXACT Excel formula: =SUM(G6:G13)/SUM(E6:E13)
    if sum(fiberWeight_g) > 0
        lam.ZeroPercent = sum(zeroFiber_g) / sum(fiberWeight_g);
    else
        lam.ZeroPercent = NaN;
    end

    % EXACT Excel formula:
    % =ABS((SUMIF(C6:C13,"UD 0º",G6:G13)-((X26*0.001*X27*0.001)*X31*X21))/SUM(E6:E13))
    ud0_zero_weight = sum(zeroFiber_g(orientation == "UD 0º"));
    count_ud90 = sum(orientation == "UD 90º");
    ud90_reference_weight = area_m2 * 300 * count_ud90;

    if sum(fiberWeight_g) > 0
        lam.WarpingPercent = abs((ud0_zero_weight - ud90_reference_weight) / sum(fiberWeight_g));
    else
        lam.WarpingPercent = NaN;
    end

    lam.PlyTable = table(orientation, thickness_mm, fiberWeight_g, totalWeight_g, zeroFiber_g, ...
        'VariableNames', {'Orientation','Thickness_mm','FiberWeight_g','TotalWeight_g','ZeroFiber_g'});
end

%==========================================================================
% 3PB COMMON
%==========================================================================
function common = compute3PBCommon(base, opts)
    x = base.Data.displacement_mm(:);
    y = base.Data.load_N(:);

    [maxForce, idxMax] = max(y);
    xAsc = x(1:idxMax);
    yAsc = y(1:idxMax);

    [iBest, jBest, bestSlope] = maxSlopePair(xAsc, yAsc, opts.minSlopeDx_mm);

    x1 = xAsc(iBest);
    x2 = xAsc(jBest);
    y1 = yAsc(iBest);
    y2 = yAsc(jBest);
    b = y1 - bestSlope * x1;

    common = struct();
    common.MaxForce_N = maxForce;
    common.LinearRegion = struct( ...
        'x1_mm', x1, ...
        'x2_mm', x2, ...
        'y1_N', y1, ...
        'y2_N', y2, ...
        'slope_N_per_mm', bestSlope, ...
        'intercept_N', b);
end

function [iBest, jBest, bestSlope] = maxSlopePair(x, y, minDx)
    n = numel(x);
    iBest = 1;
    jBest = 2;
    bestSlope = -inf;

    for i = 1:n-1
        dx = x(i+1:n) - x(i);
        valid = dx >= minDx;
        if ~any(valid)
            continue;
        end
        jj = find(valid) + i;
        slopes = (y(jj) - y(i)) ./ (x(jj) - x(i));
        [mx, idx] = max(slopes);
        if mx > bestSlope
            bestSlope = mx;
            iBest = i;
            jBest = jj(idx);
        end
    end

    if ~isfinite(bestSlope)
        error('No valid pair found with dx >= %.3f mm.', minDx);
    end
end

function r = compute3PBAllWorkbookFormulas(r, panelCode, opts)
    obj = getWorkbookPanelConstants(panelCode);

    D17 = r.Metadata.CoreThickness_mm;
    D18 = r.Metadata.SkinThickness_mm;
    X27 = opts.specimenLength_mm;
    L7 = obj.panelHeight_mm;

    plyThickness = r.LaminateInfo.ThicknessPerPly_mm;
    D6D13_sum = sum(plyThickness);

    AB4 = (X27 * (((D17 + D6D13_sum*2)^3) - (D17^3)) / 12);
    AB5 = (r.MaxForce_N * opts.span_mm * 0.5 * (D17 + 2*D18) / (4 * AB4)) * 1000000;

    L15 = secondMomentPanel(D17, D18, L7);
    L16 = L15 / 10^12;

    J11 = r.LinearRegion.slope_N_per_mm;
    J10 = r.LinearRegion.x2_mm;
    J9  = r.LinearRegion.x1_mm;

    K18 = ((J11*(J10-J9)*opts.span_mm^3) / (48*AB4*(J10-J9))) * 0.001;
    if (J10 - J9) < 1
        K21 = NaN;
        K21_msg = "Distancia entre x1 y x2 < 1mm";
    else
        K21 = K18 * 10^9 * L16;
        K21_msg = "";
    end

    T8  = obj.YieldTarget_N;
    T14 = obj.UTSTarget_N;
    T20 = obj.MaxLoadTarget_N;
    T26 = obj.MaxDeflectionTarget_m;
    T32 = obj.EnergyTarget_J;

    AB27 = ((D17 + 2*D18) - D17) * L7;

    T7  = AB27 * AB5 / 1000000;
    T13 = AB27 * AB5 / 1000000;
    T19 = 4 * AB5 * L16 / (0.001 * 0.5 * (D17 + 2*D18));

    if strcmpi(panelCode,"SISv") || strcmpi(panelCode,"SISh")
        T9  = NaN;
        T15 = NaN;
        T21 = NaN;
        T27 = NaN;
        T33 = NaN;
    else
        T9  = T7  / T8;
        T15 = T13 / T14;
        T21 = T19 / T20;
        T27 = (T20 / (48*K21)) / T26;
        T33 = (0.5*T19*(T19/(48*K21))) / T32;
    end

    T25 = T20 / (48*K21);
    T31 = 0.5 * T19 * (T19 / (48*K21));

    r.SES = struct();
    r.SES.AB4_ProbeSecondMoment_mm4 = AB4;
    r.SES.AB5_SigmaUTS_Pa = AB5;
    r.SES.L15_PanelSecondMoment_mm4 = L15;
    r.SES.L16_PanelSecondMoment_m4 = L16;
    r.SES.K18_E_GPa = K18;
    r.SES.K21_EI_GPa_m4 = K21;
    r.SES.K21_Message = K21_msg;

    r.SES.YieldTensileStrength_Probe_N = T7;
    r.SES.YieldTensileStrength_Target_N = T8;
    r.SES.CS_YieldTensileStrength = T9;

    r.SES.UTS_Probe_N = T13;
    r.SES.UTS_Target_N = T14;
    r.SES.CS_UTS = T15;

    r.SES.MaxLoadAtMidspan_Probe_N = T19;
    r.SES.MaxLoadAtMidspan_Target_N = T20;
    r.SES.CS_MaxLoadAtMidspan = T21;

    r.SES.MaxDeflectionAtBaseline_Probe_m = T25;
    r.SES.MaxDeflectionAtBaseline_Target_m = T26;
    r.SES.CS_MaxDeflectionAtBaseline = T27;

    r.SES.EnergyAbsorbed_Probe_J = T31;
    r.SES.EnergyAbsorbed_Target_J = T32;
    r.SES.CS_EnergyAbsorbed = T33;

    r.SES.EI_Target_GPa_m4 = obj.EI_Target_GPa_m4;
    r.SES.CS_EI = K21 / obj.EI_Target_GPa_m4;
end

function L15 = secondMomentPanel(D17, D18, L7)
    X5 = L7;
    X6 = D18;
    Y5 = L7;
    Y6 = D18;
    X8 = X5 * X6;
    X9 = Y5 * Y6;
    X10 = X6 / 2;
    X11 = ((D17 + 2*D18) - 0.5*D18);
    X12 = (X8*X10 + X9*X11) / (X8 + X9);
    Z8 = (X5 * X6^3) / 12;
    Z9 = (Y5 * Y6^3) / 12;
    Z10 = Z8 + (X8 * (X12 - X10)^2);
    Z11 = Z9 + (X9 * (X12 - X11)^2);
    Z12 = Z10 + Z11;
    L15 = Z12;
end

%==========================================================================
% SHEAR COMMON
%==========================================================================
function common = computeShearCommon(base, opts)
    x = base.Data.displacement_mm(:);
    y = base.Data.load_N(:);

    if isempty(opts.minPeakDistance_mm)
        minPeakDistance_mm = max(1.0, 0.20*(max(x)-min(x)));
    else
        minPeakDistance_mm = opts.minPeakDistance_mm;
    end

    prom = opts.peakProminenceFraction * max(abs(y));

    try
        [pks, locs] = findpeaks(y, x, ...
            'MinPeakDistance', minPeakDistance_mm, ...
            'MinPeakProminence', prom);
    catch
        [pks, locs] = findpeaks(y, x, ...
            'MinPeakDistance', minPeakDistance_mm);
    end

    if numel(pks) < 2
        [pks, locs] = fallbackTwoSeparatedPeaks(x, y, minPeakDistance_mm);
    end

    [highPk, lowPk, xHigh, xLow] = pickHighAndLowPeak(pks, locs);

    common = struct();
    common.Shear = struct();
    common.Shear.HighestPeak_N = highPk;
    common.Shear.LowestPeak_N = lowPk;
    common.Shear.HighestPeak_x_mm = xHigh;
    common.Shear.LowestPeak_x_mm = xLow;
end

function r = computeShearAllWorkbookFormulas(r, panelCode)
    obj = getWorkbookPanelConstants(panelCode);

    P6 = r.Shear.LowestPeak_N;
    P7 = r.Shear.HighestPeak_N;
    D18 = r.Metadata.SkinThickness_mm;

    if isnan(D18) || D18 == 0
        P8 = NaN;
    else
        switch string(panelCode)
            case {"FBH","FHB","SHB","MHBS","SISh"}
                P8 = P6 / (pi * 25 * D18);
            case {"FBHS","SISv"}
                P8 = P7 / (pi * 25 * D18);
            otherwise
                P8 = NaN;
        end
    end

    if strcmpi(panelCode,"FBH")
        P11 = (obj.OuterWidth_mm + obj.OuterHeight_mm) * 0.002 * (D18/1000) * P8 * 10^6;
        P12 = 510000;
        P13 = P11 / P12;
    else
        P11 = NaN;
        P12 = NaN;
        P13 = NaN;
    end

    r.Shear.ShearStress_MPa = P8;
    r.Shear.PerimeterShear_Probe_N = P11;
    r.Shear.PerimeterShear_Target_N = P12;
    r.Shear.CS_PerimeterShear = P13;
end

function [pks, locs] = fallbackTwoSeparatedPeaks(x, y, minDist)
    [ys, idx] = sort(y, 'descend');
    xs = x(idx);

    chosen = false(size(ys));
    chosenX = [];

    for k = 1:numel(ys)
        if isempty(chosenX) || all(abs(xs(k) - chosenX) >= minDist)
            chosen(k) = true;
            chosenX(end+1) = xs(k); %#ok<AGROW>
        end
        if nnz(chosen) >= 2
            break;
        end
    end

    pks = ys(chosen);
    locs = xs(chosen);

    if numel(pks) < 2
        [~, i1] = max(y);
        mask = abs(x - x(i1)) >= minDist;
        if any(mask)
            idx2all = find(mask);
            [~, ir] = max(y(mask));
            i2 = idx2all(ir);
        else
            [~, ord] = sort(y, 'descend');
            i2 = ord(min(2,numel(ord)));
        end
        pks = [y(i1); y(i2)];
        locs = [x(i1); x(i2)];
    end
end

function [highPk, lowPk, xHigh, xLow] = pickHighAndLowPeak(pks, locs)
    [~, ord] = sort(pks, 'descend');
    top = ord(1:min(2,numel(ord)));

    p2 = pks(top);
    x2 = locs(top);

    highPk = max(p2);
    lowPk = min(p2);

    xHigh = x2(find(p2 == highPk, 1, 'first'));
    xLow  = x2(find(p2 == lowPk, 1, 'first'));
end

%==========================================================================
% PANEL CONSTANTS
%==========================================================================
function obj = getWorkbookPanelConstants(panelCode)
    code = string(panelCode);

    switch code
        case "FBH"
            obj.panelHeight_mm = 149.98;
            obj.YieldTarget_N = 73000;
            obj.UTSTarget_N = 87300;
            obj.MaxLoadTarget_N = 1960;
            obj.MaxDeflectionTarget_m = 0.012;
            obj.EnergyTarget_J = 11.7;
            obj.EI_Target_GPa_m4 = 3400;
        case "FHB"
            obj.panelHeight_mm = 121.68;
            obj.YieldTarget_N = 36500;
            obj.UTSTarget_N = 43700;
            obj.MaxLoadTarget_N = 978;
            obj.MaxDeflectionTarget_m = 0.012;
            obj.EnergyTarget_J = 5.86;
            obj.EI_Target_GPa_m4 = 1700;
        case "FBHS"
            obj.panelHeight_mm = 337.81;
            obj.YieldTarget_N = 83500;
            obj.UTSTarget_N = 99900;
            obj.MaxLoadTarget_N = 2310;
            obj.MaxDeflectionTarget_m = 0.012;
            obj.EnergyTarget_J = 13.8;
            obj.EI_Target_GPa_m4 = 4020;
        case "SHB"
            obj.panelHeight_mm = 101.29;
            obj.YieldTarget_N = 52900;
            obj.UTSTarget_N = 63300;
            obj.MaxLoadTarget_N = 1330;
            obj.MaxDeflectionTarget_m = 0.012;
            obj.EnergyTarget_J = 7.98;
            obj.EI_Target_GPa_m4 = 2320;
        case "MHBS"
            obj.panelHeight_mm = 248.17;
            obj.YieldTarget_N = 55700;
            obj.UTSTarget_N = 66600;
            obj.MaxLoadTarget_N = 1540;
            obj.MaxDeflectionTarget_m = 0.012;
            obj.EnergyTarget_J = 9.22;
            obj.EI_Target_GPa_m4 = 2680;
        case "SISv"
            obj.panelHeight_mm = 274.86;
            obj.YieldTarget_N = 109000;
            obj.UTSTarget_N = 131000;
            obj.MaxLoadTarget_N = 2930;
            obj.MaxDeflectionTarget_m = 0.012;
            obj.EnergyTarget_J = 17.6;
            obj.EI_Target_GPa_m4 = 5110;
        case "SISh"
            obj.panelHeight_mm = 185.40;
            obj.YieldTarget_N = 109000;
            obj.UTSTarget_N = 131000;
            obj.MaxLoadTarget_N = 2930;
            obj.MaxDeflectionTarget_m = 0.012;
            obj.EnergyTarget_J = 17.6;
            obj.EI_Target_GPa_m4 = 5110;
        otherwise
            error('Unknown panel code "%s".', panelCode);
    end

    obj.OuterWidth_mm = 313.98;
    obj.OuterHeight_mm = 314.00;
end

%==========================================================================
% PLOT 3PB
%==========================================================================
function plot3PB_clean(base, common)
    x = base.Data.displacement_mm(:);
    y_kN = base.Data.load_N(:) / 1000;

    valid = (x > 0) & (y_kN > 0);
    xPlot = x(valid);
    yPlot = y_kN(valid);

    if isempty(xPlot)
        warning('No positive x>0 and y>0 data available for plotting.');
        return;
    end

    x1 = common.LinearRegion.x1_mm;
    x2 = common.LinearRegion.x2_mm;
    y1 = common.LinearRegion.y1_N / 1000;
    y2 = common.LinearRegion.y2_N / 1000;
    m  = common.LinearRegion.slope_N_per_mm / 1000;
    b  = common.LinearRegion.intercept_N / 1000;

    figure('Color','w','Position',[100 100 900 550]);

    plot(xPlot, yPlot, 'LineWidth', 2.1, 'Color', [0 0 0]);
    hold on;
    grid on;

    guideColor = [0.45 0.45 0.45];

    if x1 > 0 && y1 > 0
        h = plot([x1 x1], [0 y1], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');

        h = plot([0 x1], [y1 y1], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');
    end

    if x2 > 0 && y2 > 0
        h = plot([x2 x2], [0 y2], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');

        h = plot([0 x2], [y2 y2], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');
    end

    plot([x1 x2], [y1 y2], 'o', ...
        'MarkerSize', 8, ...
        'MarkerFaceColor', [1 0.5 0], ...
        'MarkerEdgeColor', [0.6 0.3 0], ...
        'LineWidth', 1.0);

    xx = linspace(min(xPlot), max(xPlot), 400);
    yy = m*xx + b;
    fitValid = (xx > 0) & (yy > 0);

    plot(xx(fitValid), yy(fitValid), '--', ...
        'LineWidth', 1.7, ...
        'Color', [0.72 0.72 0.72]);

    xlabel('Displacement [mm]', 'FontSize', 12, 'FontWeight', 'bold');
    ylabel('Load [kN]', 'FontSize', 12, 'FontWeight', 'bold');
    title('Load - Displacement', 'FontSize', 14, 'FontWeight', 'bold');

    ax = gca;
    ax.Box = 'on';
    ax.LineWidth = 1.1;
    ax.FontSize = 11;
    ax.GridAlpha = 0.12;
    ax.MinorGridAlpha = 0.06;
    ax.XMinorGrid = 'on';
    ax.YMinorGrid = 'on';

    xlim([0 max(xPlot)*1.03]);
    ylim([0 max(yPlot)*1.05]);

    eqText = sprintf('y = %s x %s %s', fmtNum(m,4), ternary(b>=0,'+','-'), fmtNum(abs(b),4));
    xl = xlim;
    yl = ylim;
    xt = xl(1) + 0.70*(xl(2)-xl(1));
    yt = yl(1) + 0.90*(yl(2)-yl(1));

    text(xt, yt, eqText, ...
        'FontSize', 11, ...
        'FontWeight', 'bold', ...
        'BackgroundColor', 'white', ...
        'EdgeColor', [0.75 0.75 0.75], ...
        'Margin', 6);

    legend off
end

%==========================================================================
% PLOT SHEAR
%==========================================================================
function plotShear_clean(base, common)
    x = base.Data.displacement_mm(:);
    y_kN = base.Data.load_N(:) / 1000;

    valid = (x > 0) & (y_kN > 0);
    xPlot = x(valid);
    yPlot = y_kN(valid);

    if isempty(xPlot)
        warning('No positive x>0 and y>0 data available for plotting.');
        return;
    end

    xHigh = common.Shear.HighestPeak_x_mm;
    yHigh = common.Shear.HighestPeak_N / 1000;
    xLow  = common.Shear.LowestPeak_x_mm;
    yLow  = common.Shear.LowestPeak_N / 1000;

    figure('Color','w','Position',[100 100 900 550]);

    plot(xPlot, yPlot, 'LineWidth', 2.1, 'Color', [0 0 0]);
    hold on;
    grid on;

    guideColor = [0.45 0.45 0.45];

    if xHigh > 0 && yHigh > 0
        h = plot([xHigh xHigh], [0 yHigh], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');

        h = plot([0 xHigh], [yHigh yHigh], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');
    end

    if xLow > 0 && yLow > 0
        h = plot([xLow xLow], [0 yLow], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');

        h = plot([0 xLow], [yLow yLow], ':', 'Color', guideColor, 'LineWidth', 1.15);
        set(get(get(h,'Annotation'),'LegendInformation'),'IconDisplayStyle','off');
    end

    xlabel('Displacement [mm]', 'FontSize', 12, 'FontWeight', 'bold');
    ylabel('Load [kN]', 'FontSize', 12, 'FontWeight', 'bold');
    title('Load - Displacement', 'FontSize', 14, 'FontWeight', 'bold');

    ax = gca;
    ax.Box = 'on';
    ax.LineWidth = 1.1;
    ax.FontSize = 11;
    ax.GridAlpha = 0.12;
    ax.MinorGridAlpha = 0.06;
    ax.XMinorGrid = 'on';
    ax.YMinorGrid = 'on';

    xlim([0 max(xPlot)*1.03]);
    ylim([0 max(yPlot)*1.05]);

    legend off
end

%==========================================================================
% OUTPUT TABLE FORMATTING
%==========================================================================
function row = resultToRowFormatted(r)
    base = table( ...
        string(r.PanelCode), ...
        string(r.Mode), ...
        string(r.Metadata.SpecimenID), ...
        string(r.Metadata.Type), ...
        string(r.Metadata.Date), ...
        string(r.Metadata.CFType), ...
        string(r.Metadata.Laminate), ...
        string(r.Metadata.CoreMaterial), ...
        fmtNum(r.Metadata.CoreThickness_mm,4), ...
        fmtNum(r.Metadata.Height_mm,4), ...
        fmtNum(r.Metadata.Width_mm,4), ...
        fmtNum(r.Metadata.Thickness_mm,4), ...
        fmtNum(r.Metadata.Weight_g,4), ...
        fmtNum(r.Metadata.SkinThickness_mm,4), ...
        fmtPercent(r.LaminateInfo.ZeroPercent,4), ...
        fmtPercent(r.LaminateInfo.WarpingPercent,4), ...
        fmtNum(r.MaxForce_N,4), ...
        'VariableNames', { ...
        'PanelCode','Mode','SpecimenID','Type','Date','CFType', ...
        'Laminate','CoreMaterial','CoreThickness_mm','Height_mm','Width_mm', ...
        'Thickness_mm','Weight_g','SkinThickness_mm','ZeroPercent','WarpingPercent','MaxForce_N'});

    if r.Mode == "3PBT"
        extra = table( ...
            fmtNum(r.LinearRegion.x1_mm,4), ...
            fmtNum(r.LinearRegion.x2_mm,4), ...
            fmtNum(r.LinearRegion.y1_N,4), ...
            fmtNum(r.LinearRegion.y2_N,4), ...
            fmtNum(r.LinearRegion.slope_N_per_mm,4), ...
            fmtNum(r.LinearRegion.intercept_N,4), ...
            fmtNum(r.SES.K21_EI_GPa_m4,4), ...
            fmtNum(r.SES.CS_EI,4), ...
            fmtNum(r.SES.YieldTensileStrength_Probe_N,4), ...
            fmtNum(r.SES.CS_YieldTensileStrength,4), ...
            fmtNum(r.SES.UTS_Probe_N,4), ...
            fmtNum(r.SES.CS_UTS,4), ...
            fmtNum(r.SES.MaxLoadAtMidspan_Probe_N,4), ...
            fmtNum(r.SES.CS_MaxLoadAtMidspan,4), ...
            fmtNum(r.SES.MaxDeflectionAtBaseline_Probe_m,6), ...
            fmtNum(r.SES.CS_MaxDeflectionAtBaseline,4), ...
            fmtNum(r.SES.EnergyAbsorbed_Probe_J,4), ...
            fmtNum(r.SES.CS_EnergyAbsorbed,4), ...
            'VariableNames', { ...
            'x1_mm','x2_mm','y1_N','y2_N','Slope_N_per_mm','Intercept_N', ...
            'EI_GPa_m4','CS_EI','Yield_N','CS_Yield','UTS_N','CS_UTS', ...
            'MaxLoadMidspan_N','CS_MaxLoadMidspan','MaxDeflection_m', ...
            'CS_MaxDeflection','EnergyAbsorbed_J','CS_Energy'});
    else
        extra = table( ...
            fmtNum(r.Shear.HighestPeak_x_mm,4), ...
            fmtNum(r.Shear.HighestPeak_N,4), ...
            fmtNum(r.Shear.LowestPeak_x_mm,4), ...
            fmtNum(r.Shear.LowestPeak_N,4), ...
            fmtNum(getfield_safe(r.Shear,'ShearStress_MPa'),4), ...
            fmtNum(getfield_safe(r.Shear,'PerimeterShear_Probe_N'),4), ...
            fmtNum(getfield_safe(r.Shear,'CS_PerimeterShear'),4), ...
            'VariableNames', { ...
            'HighestPeak_x_mm','HighestPeak_N','LowestPeak_x_mm','LowestPeak_N', ...
            'ShearStress_MPa','PerimeterShear_N','CS_PerimeterShear'});
    end

    row = [base extra];
end

function out = fmtNum(v, nd)
    if nargin < 2
        nd = 4;
    end
    if ischar(v) || isstring(v)
        out = string(v);
        return;
    end
    if isempty(v) || ~isfinite(v)
        out = "NA";
        return;
    end
    s = sprintf(['%0.' num2str(nd) 'f'], v);
    s = strrep(s, '.', ',');
    out = string(s);
end

function out = fmtPercent(v, nd)
    if nargin < 2
        nd = 4;
    end
    if isempty(v) || ~isfinite(v)
        out = "NA";
        return;
    end
    s = sprintf(['%0.' num2str(nd) 'f'], 100*v);
    s = strrep(s, '.', ',');
    out = string(s);
end

function out = ternary(cond, a, b)
    if cond
        out = a;
    else
        out = b;
    end
end

function v = getfield_safe(S, fname)
    if isfield(S, fname)
        v = S.(fname);
    else
        v = NaN;
    end
end

%==========================================================================
% HELPERS
%==========================================================================
function n = toNumber(v)
    if isnumeric(v)
        n = double(v);
        return;
    end

    if isempty(v) || ismissing(v)
        n = NaN;
        return;
    end

    s = strtrim(string(v));

    if contains(s, ",") && ~contains(s, ".")
        s = replace(s, ",", ".");
    elseif contains(s, ",") && contains(s, ".")
        s = replace(s, ".", "");
        s = replace(s, ",", ".");
    end

    s = regexprep(s, '[^\d\.\-eE+]', '');
    n = str2double(s);
end

function s = cellToString(v)
    if isstring(v)
        s = v;
    elseif ischar(v)
        s = string(v);
    elseif isnumeric(v)
        s = string(v);
    elseif isdatetime(v)
        s = string(v);
    elseif isempty(v)
        s = "";
    else
        s = string(v);
    end
end

%==========================================================================
% PRINT SUMMARY
%==========================================================================
function printSummary(r)
    fprintf('\n----------------------------------------\n');
    fprintf('Panel code used for calculation: %s\n', r.PanelCode);
    fprintf('0 deg %%   : %s\n', fmtPercent(r.LaminateInfo.ZeroPercent,4));
    fprintf('Warping %% : %s\n', fmtPercent(r.LaminateInfo.WarpingPercent,4));

    if r.Mode == "3PBT"
        fprintf('x1 = %s mm | x2 = %s mm\n', fmtNum(r.LinearRegion.x1_mm,4), fmtNum(r.LinearRegion.x2_mm,4));
        fprintf('y1 = %s N  | y2 = %s N\n', fmtNum(r.LinearRegion.y1_N,4), fmtNum(r.LinearRegion.y2_N,4));
        fprintf('Slope = %s N/mm\n', fmtNum(r.LinearRegion.slope_N_per_mm,4));
        fprintf('Max Force = %s N\n', fmtNum(r.MaxForce_N,4));
        fprintf('EI = %s GPa/m^4\n', fmtNum(r.SES.K21_EI_GPa_m4,4));
        fprintf('CS EI = %s\n', fmtNum(r.SES.CS_EI,4));
        fprintf('CS Yield = %s\n', fmtNum(r.SES.CS_YieldTensileStrength,4));
        fprintf('CS UTS = %s\n', fmtNum(r.SES.CS_UTS,4));
        fprintf('CS Midspan = %s\n', fmtNum(r.SES.CS_MaxLoadAtMidspan,4));
        fprintf('CS Deflection = %s\n', fmtNum(r.SES.CS_MaxDeflectionAtBaseline,4));
        fprintf('CS Energy = %s\n', fmtNum(r.SES.CS_EnergyAbsorbed,4));
    else
        fprintf('Highest peak = %s N at x = %s mm\n', fmtNum(r.Shear.HighestPeak_N,4), fmtNum(r.Shear.HighestPeak_x_mm,4));
        fprintf('Lowest peak  = %s N at x = %s mm\n', fmtNum(r.Shear.LowestPeak_N,4), fmtNum(r.Shear.LowestPeak_x_mm,4));
        fprintf('Shear stress = %s MPa\n', fmtNum(getfield_safe(r.Shear,'ShearStress_MPa'),4));
        if ~isnan(getfield_safe(r.Shear,'CS_PerimeterShear'))
            fprintf('CS Perimeter Shear = %s\n', fmtNum(r.Shear.CS_PerimeterShear,4));
        end
    end
end