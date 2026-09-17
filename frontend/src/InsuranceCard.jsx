const STATUS_LABEL = {
  eligible: 'Eligible',
  coverage_lapsed: 'Coverage lapsed',
  approved: 'Approved',
  under_review: 'Under review',
}

export default function InsuranceCard({ insurance }) {
  if (!insurance) return null
  const hasPolicy = Boolean(insurance.insurer)

  return (
    <div className="insurance-card">
      <div className="insurance-card-banner">SIMULATED INSURANCE CONNECT</div>
      {hasPolicy ? (
        <div className="insurance-card-body">
          <div className="insurance-row">
            <span className="insurance-label">Insurer</span>
            <span>{insurance.insurer}</span>
          </div>
          <div className="insurance-row">
            <span className="insurance-label">Policy</span>
            <span>{insurance.policy_number}</span>
          </div>
          <div className="insurance-row">
            <span className="insurance-label">Eligibility</span>
            <span className={`insurance-status insurance-status-${insurance.eligibility_status}`}>
              {STATUS_LABEL[insurance.eligibility_status] ?? insurance.eligibility_status}
            </span>
          </div>
          {insurance.last_claim && (
            <>
              <div className="insurance-divider" />
              <div className="insurance-row">
                <span className="insurance-label">Last claim</span>
                <span>{insurance.last_claim.claim_id}</span>
              </div>
              <div className="insurance-row">
                <span className="insurance-label">Amount (est.)</span>
                <span>{insurance.last_claim.amount_estimate} units</span>
              </div>
              <div className="insurance-row">
                <span className="insurance-label">Status</span>
                <span className={`insurance-status insurance-status-${insurance.last_claim.status}`}>
                  {STATUS_LABEL[insurance.last_claim.status] ?? insurance.last_claim.status}
                </span>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="insurance-card-body">
          <p className="source-note">No eligibility check recorded yet for this encounter.</p>
        </div>
      )}
      <div className="id-card-disclaimer">{insurance.disclaimer}</div>
    </div>
  )
}
