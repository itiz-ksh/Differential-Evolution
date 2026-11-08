import React, {cloneElement, useId} from 'react';

// Shared descriptions are available both on pointer hover and keyboard focus.
export default function InfoField({label, help, children}) {
 const id=useId();
 return <label className="field"><span>{label} <span className="help-indicator" aria-hidden="true">ⓘ</span></span>{cloneElement(children, {'aria-describedby': id})}<span className="field-tooltip" id={id} role="tooltip">{help}</span></label>;
}
