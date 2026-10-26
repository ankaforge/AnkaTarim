const formatDate = (isoDate) =>
  isoDate ? new Date(`${isoDate}T00:00:00`).toLocaleDateString("tr-TR") : "";

function SubscriptionBanner({ access, isCompanyAdmin }) {
  if (!access) return null;

  if (access.state === "grace") {
    return (
      <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">
        {access.message} Kalan süre: {access.days_left} gün.
      </div>
    );
  }

  const graceModules = (access.packages || []).filter(
    (item) => item.state === "grace",
  );
  if (isCompanyAdmin && graceModules.length) {
    return (
      <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">
        Süresi dolan paket: {graceModules.map((item) => item.name).join(", ")}.
        Ek süre bitince bu paketin ekranları kapanacaktır.
      </div>
    );
  }

  if (
    isCompanyAdmin &&
    access.state === "active" &&
    access.days_left !== null &&
    access.days_left <= access.warning_days
  ) {
    return (
      <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
        Paketinizin süresi {formatDate(access.ends_on)} tarihinde doluyor (
        {access.days_left} gün kaldı). Yenileme için AnkaForge ile iletişime
        geçin.
      </div>
    );
  }

  return null;
}

export default SubscriptionBanner;
